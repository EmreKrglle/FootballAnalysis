# -*- coding: utf-8 -*-
"""
=============================================================================
FootballAnalysis - Geriden Oyun Kurma Siniflandirici
=============================================================================
4 Sinif:
    0 -> Tehlikeli Kayip  (kendi yarisinda top kaybi)
    1 -> Notr Kayip       (rakip yarisinda top kaybi)
    2 -> Ilerleme         (faul / rakip yarisina gecis)
    3 -> Yuksek Tehlike   (sut / ceza sahasina giris)
=============================================================================
"""

from __future__ import annotations
import math
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch_geometric.nn import MessagePassing
from torch_geometric.nn import global_mean_pool

# ---------------------------------------------------------
#  SINIF HARITASI - Turkce karakter YOK
# ---------------------------------------------------------
OUTCOME_TO_IDX = {
    "Tehlikeli Kayip": 0,
    "Notr Kayip":      1,
    "Ilerleme":        2,
    "Yuksek Tehlike":  3,
}
IDX_TO_OUTCOME = {v: k for k, v in OUTCOME_TO_IDX.items()}
NUM_CLASSES    = 4


# ---------------------------------------------------------
#  BOLUM 1 - ON ISLEME
# ---------------------------------------------------------

ROLE_ACTOR      = 0
ROLE_TEAMMATE   = 1
ROLE_GOALKEEPER = 2

def encode_role(actor: bool, teammate: bool, keeper: bool) -> int:
    if actor:
        return ROLE_ACTOR
    if keeper:
        return ROLE_GOALKEEPER
    return ROLE_TEAMMATE

def freeze_frames_to_node_features(
    freeze_rows: list,
    pass_success_rates: list = None,
) -> torch.Tensor:
    N = len(freeze_rows)
    if pass_success_rates is None:
        pass_success_rates = [0.75] * N

    feats = []
    for i, row in enumerate(freeze_rows):
        x_norm  = float(row['x']) / 120.0
        y_norm  = float(row['y']) / 80.0
        role    = encode_role(row['actor'], row['teammate'], row['keeper'])
        one_hot = [0.0, 0.0, 0.0]
        one_hot[role] = 1.0
        psr     = float(pass_success_rates[i])
        feats.append([x_norm, y_norm] + one_hot + [psr])

    return torch.tensor(feats, dtype=torch.float)


# ---------------------------------------------------------
#  BOLUM 2 - KENAR INSASI
# ---------------------------------------------------------

def build_player_edges(
    x_positions: torch.Tensor,
    distance_threshold: float = 0.25,
    fully_connected: bool = False,
) -> Tuple[torch.Tensor, torch.Tensor]:
    N = x_positions.size(0)
    src_list, dst_list, attr_list = [], [], []

    for i in range(N):
        for j in range(N):
            if i == j:
                continue
            dx   = x_positions[i, 0] - x_positions[j, 0]
            dy   = x_positions[i, 1] - x_positions[j, 1]
            dist = math.sqrt(dx.item()**2 + dy.item()**2)

            if not fully_connected and dist > distance_threshold:
                continue

            pass_difficulty = min(dist / 0.5, 1.0)
            under_pressure  = 1.0 if dist < 0.10 else 0.0

            src_list.append(i)
            dst_list.append(j)
            attr_list.append([dist, pass_difficulty, under_pressure])

    if len(src_list) == 0:
        src_list, dst_list = [0], [1]
        attr_list = [[0.0, 0.0, 0.0]]

    edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
    edge_attr  = torch.tensor(attr_list, dtype=torch.float)
    return edge_index, edge_attr


def build_master_edges(num_players: int) -> Tuple[torch.Tensor, torch.Tensor]:
    player_ids = torch.arange(num_players, dtype=torch.long)
    master_ids = torch.zeros(num_players, dtype=torch.long)
    up_edge_index   = torch.stack([player_ids, master_ids], dim=0)
    down_edge_index = torch.stack([master_ids, player_ids], dim=0)
    return up_edge_index, down_edge_index


# ---------------------------------------------------------
#  BOLUM 3 - OZEL GAT KATMANI
# ---------------------------------------------------------

class EdgeAwareGATConv(MessagePassing):
    def __init__(self, in_channels, out_channels, edge_dim=3, heads=4, dropout=0.1):
        super().__init__(aggr='add', node_dim=0)

        self.in_channels  = in_channels
        self.out_channels = out_channels
        self.heads        = heads
        self.dropout      = dropout
        self.head_dim     = out_channels // heads

        assert out_channels % heads == 0

        self.W_msg    = nn.Linear(in_channels, out_channels, bias=False)
        self.att_proj = nn.Linear(2 * out_channels + edge_dim, heads, bias=False)
        self.edge_proj= nn.Linear(edge_dim, out_channels, bias=False)
        self.norm     = nn.LayerNorm(out_channels)

        nn.init.xavier_uniform_(self.W_msg.weight)
        nn.init.xavier_uniform_(self.att_proj.weight)
        nn.init.xavier_uniform_(self.edge_proj.weight)

    def forward(self, x, edge_index, edge_attr=None):
        out = self.propagate(edge_index, x=x, edge_attr=edge_attr, size=None)
        return self.norm(out)

    def message(self, x_i, x_j, edge_attr):
        h_i = self.W_msg(x_i)
        h_j = self.W_msg(x_j)

        if edge_attr is None:
            edge_attr = torch.zeros(h_j.size(0), 3, device=h_j.device, dtype=h_j.dtype)

        concat  = torch.cat([h_i, h_j, edge_attr], dim=-1)
        att_raw = self.att_proj(concat)
        att_raw = F.leaky_relu(att_raw, negative_slope=0.2)
        att     = torch.sigmoid(att_raw)
        att     = F.dropout(att, p=self.dropout, training=self.training)

        h_j_heads = h_j.view(-1, self.heads, self.head_dim)
        att_exp   = att.unsqueeze(-1)
        msg       = (att_exp * h_j_heads).view(-1, self.out_channels)
        msg       = msg + self.edge_proj(edge_attr)
        return msg

    def update(self, aggr_out):
        return F.elu(aggr_out)


# ---------------------------------------------------------
#  BOLUM 4 - HETEROJEN GNN KATMANI
# ---------------------------------------------------------

class BuildupHeteroConv(nn.Module):
    def __init__(self, player_in, master_in, hidden_dim, edge_dim=3, heads=4):
        super().__init__()
        self.hidden_dim = hidden_dim

        self.player_to_player      = EdgeAwareGATConv(player_in, hidden_dim, edge_dim, heads)
        self.player_to_master_proj = nn.Linear(player_in, hidden_dim)
        self.master_update_norm    = nn.LayerNorm(hidden_dim)
        self.master_to_player_proj = nn.Linear(master_in, hidden_dim)
        self.master_gate = nn.Sequential(
            nn.Linear(hidden_dim + hidden_dim, hidden_dim),
            nn.Sigmoid(),
        )
        self.player_out_proj = nn.Linear(hidden_dim, hidden_dim)
        self.player_norm     = nn.LayerNorm(hidden_dim)

    def forward(self, x_player, x_master, edge_pp, edge_attr_pp, edge_pm, edge_mp):
        N_p = x_player.size(0)
        N_m = x_master.size(0)

        # Oyuncu -> Oyuncu
        h_pp = self.player_to_player(x_player, edge_pp, edge_attr_pp)

        # Oyuncu -> Master (scatter mean)
        player_msgs    = self.player_to_master_proj(x_player)
        master_dst_idx = edge_pm[1]
        h_master_agg   = torch.zeros(N_m, self.hidden_dim, device=x_master.device)
        h_master_count = torch.zeros(N_m, 1, device=x_master.device)
        h_master_agg.scatter_add_(0, master_dst_idx.unsqueeze(1).expand_as(player_msgs), player_msgs)
        ones = torch.ones(N_p, 1, device=x_master.device)
        h_master_count.scatter_add_(0, master_dst_idx.unsqueeze(1), ones)
        h_master_count = h_master_count.clamp(min=1.0)
        h_master_agg   = h_master_agg / h_master_count
        h_master_new   = self.master_update_norm(h_master_agg)

        # Master -> Oyuncu
        master_src_idx   = edge_mp[0]
        master_context   = self.master_to_player_proj(h_master_new)
        master_broadcast = master_context[master_src_idx]

        # Gating
        gate_input        = torch.cat([h_pp, master_broadcast], dim=-1)
        gate              = self.master_gate(gate_input)
        h_player_combined = gate * h_pp + (1.0 - gate) * master_broadcast
        h_player_new      = self.player_norm(F.elu(self.player_out_proj(h_player_combined)))

        return h_player_new, h_master_new


# ---------------------------------------------------------
#  BOLUM 5 - TAM MODEL
# ---------------------------------------------------------

class BuildupPlayGNN(nn.Module):
    NODE_FEAT_DIM   = 6
    MASTER_FEAT_DIM = 3
    EDGE_FEAT_DIM   = 3

    def __init__(
        self,
        node_feat_dim:   int   = 6,
        master_feat_dim: int   = 3,
        edge_feat_dim:   int   = 3,
        hidden_dim:      int   = 64,
        num_layers:      int   = 3,
        dropout:         float = 0.2,
        heads:           int   = 4,
        num_classes:     int   = 4,
    ):
        super().__init__()
        self.hidden_dim  = hidden_dim
        self.num_layers  = num_layers
        self.dropout_p   = dropout
        self.num_classes = num_classes

        self.player_input_proj = nn.Sequential(
            nn.Linear(node_feat_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ELU(),
        )
        self.master_input_proj = nn.Sequential(
            nn.Linear(master_feat_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ELU(),
        )

        self.conv_layers = nn.ModuleList([
            BuildupHeteroConv(hidden_dim, hidden_dim, hidden_dim, edge_feat_dim, heads)
            for _ in range(num_layers)
        ])

        self.skip_proj = nn.Linear(node_feat_dim, hidden_dim)

        self.fusion_layer = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ELU(),
            nn.Dropout(dropout),
        )

        out_dim = num_classes if num_classes > 1 else 1
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, out_dim),
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x_dict, edge_index_dict, edge_attr_dict, batch=None):
        x_player_raw = x_dict['player']
        x_master_raw = x_dict['master']

        h_player = self.player_input_proj(x_player_raw)
        h_master = self.master_input_proj(x_master_raw)
        skip     = self.skip_proj(x_player_raw)

        edge_pp      = edge_index_dict[('player', 'passes_to',  'player')]
        edge_pm      = edge_index_dict[('player', 'reports_to', 'master')]
        edge_mp      = edge_index_dict[('master', 'informs',    'player')]
        edge_attr_pp = edge_attr_dict.get(
            ('player', 'passes_to', 'player'),
            torch.zeros(edge_pp.size(1), self.EDGE_FEAT_DIM,
                        device=h_player.device, dtype=h_player.dtype)
        )

        for i, conv in enumerate(self.conv_layers):
            h_player_new, h_master_new = conv(
                h_player, h_master, edge_pp, edge_attr_pp, edge_pm, edge_mp
            )
            h_player = h_player_new + (skip if i == 0 else h_player)
            h_master = h_master_new + h_master
            h_player = F.dropout(h_player, p=self.dropout_p, training=self.training)

        if batch is None:
            h_pool        = h_player.mean(dim=0, keepdim=True)
            h_master_pool = h_master
        else:
            h_pool        = global_mean_pool(h_player, batch)
            h_master_pool = h_master

        fused  = torch.cat([h_pool, h_master_pool], dim=-1)
        fused  = self.fusion_layer(fused)
        logits = self.classifier(fused)

        if self.num_classes == 1:
            logits = logits.squeeze(-1)

        return logits

    def predict_proba(self, x_dict, edge_index_dict, edge_attr_dict, batch=None):
        with torch.no_grad():
            logits = self.forward(x_dict, edge_index_dict, edge_attr_dict, batch)
            if self.num_classes > 1:
                return torch.softmax(logits, dim=-1)
            return torch.sigmoid(logits)


# ---------------------------------------------------------
#  BOLUM 6 - SAHTE VERI URETICI
# ---------------------------------------------------------

def create_mock_football_graph(batch_size=4, num_players=11, seed=42):
    torch.manual_seed(seed)
    N_total = batch_size * num_players

    positions    = torch.rand(N_total, 2)
    roles_raw    = torch.randint(0, 3, (N_total,))
    role_one_hot = F.one_hot(roles_raw, num_classes=3).float()
    pass_success = torch.rand(N_total, 1) * 0.4 + 0.5
    x_player     = torch.cat([positions, role_one_hot, pass_success], dim=1)

    score_diff     = torch.randint(-2, 3, (batch_size, 1)).float()
    time_remaining = torch.rand(batch_size, 1)
    pressure_index = torch.rand(batch_size, 1)
    x_master       = torch.cat([score_diff, time_remaining, pressure_index], dim=1)

    batch = torch.repeat_interleave(torch.arange(batch_size), num_players)

    all_src, all_dst, all_attr = [], [], []
    for g in range(batch_size):
        offset    = g * num_players
        local_pos = positions[offset:offset + num_players]
        ei, ea    = build_player_edges(local_pos, 0.30)
        all_src.append(ei[0] + offset)
        all_dst.append(ei[1] + offset)
        all_attr.append(ea)

    edge_index_pp = torch.stack([torch.cat(all_src), torch.cat(all_dst)], dim=0)
    edge_attr_pp  = torch.cat(all_attr, dim=0)

    player_ids    = torch.arange(N_total, dtype=torch.long)
    master_ids    = batch.long()
    edge_index_pm = torch.stack([player_ids, master_ids], dim=0)
    edge_index_mp = torch.stack([master_ids, player_ids], dim=0)

    labels = torch.randint(0, 4, (batch_size,)).long()

    x_dict = {'player': x_player, 'master': x_master}
    edge_index_dict = {
        ('player', 'passes_to',  'player'): edge_index_pp,
        ('player', 'reports_to', 'master'): edge_index_pm,
        ('master', 'informs',    'player'): edge_index_mp,
    }
    edge_attr_dict = {('player', 'passes_to', 'player'): edge_attr_pp}

    return x_dict, edge_index_dict, edge_attr_dict, batch, labels


# ---------------------------------------------------------
#  BOLUM 7 - REPO ENTEGRASYON KOPRUSU
# ---------------------------------------------------------

def sequence_to_graph(
    sequence_data: dict,
    match_context: dict,
    player_stats:  dict = None,
) -> Tuple[Dict, Dict, Dict, float]:

    events = sequence_data.get('events', [])
    if not events:
        raise ValueError("Sekans bos!")

    player_rows = []
    for ev in events[-11:]:
        player_rows.append({
            'x':        ev.get('x', 60.0) or 60.0,
            'y':        ev.get('y', 40.0) or 40.0,
            'actor':    False,
            'teammate': True,
            'keeper':   False,
        })

    while len(player_rows) < 11:
        player_rows.append({
            'x': 60.0, 'y': 40.0,
            'actor': False, 'teammate': True, 'keeper': False
        })
    player_rows = player_rows[:11]

    psr = [0.75] * 11
    if player_stats:
        for i, ev in enumerate(events[-11:]):
            pid = ev.get('player_id')
            if pid and pid in player_stats:
                psr[i] = player_stats[pid].get('pass_success_rate', 0.75)

    x_player = freeze_frames_to_node_features(player_rows, psr)

    score_diff_norm = float(match_context.get('score_diff', 0)) / 5.0
    time_norm       = float(match_context.get('time_remaining', 45.0)) / 90.0
    pressure        = float(match_context.get('pressure_index', 0.5))
    x_master        = torch.tensor([[score_diff_norm, time_norm, pressure]])

    positions             = x_player[:, :2]
    edge_pp, edge_attr_pp = build_player_edges(positions, distance_threshold=0.30)
    edge_pm, edge_mp      = build_master_edges(num_players=11)

    x_dict = {'player': x_player, 'master': x_master}
    edge_index_dict = {
        ('player', 'passes_to',  'player'): edge_pp,
        ('player', 'reports_to', 'master'): edge_pm,
        ('master', 'informs',    'player'): edge_mp,
    }
    edge_attr_dict = {('player', 'passes_to', 'player'): edge_attr_pp}

    # Etiket - Turkce karakter YOK
    outcome = sequence_data.get('outcome', 'Notr Kayip')
    label   = float(OUTCOME_TO_IDX.get(outcome, 1))

    return x_dict, edge_index_dict, edge_attr_dict, label


# ---------------------------------------------------------
#  TEST
# ---------------------------------------------------------

def run_full_test():
    print("=" * 55)
    print("  BuildupPlayGNN - Boyut Dogrulama Testi")
    print("=" * 55)

    model = BuildupPlayGNN(num_classes=4)
    x_dict, ei_dict, ea_dict, batch, labels = create_mock_football_graph(batch_size=4)

    model.eval()
    with torch.no_grad():
        logits = model(x_dict, ei_dict, ea_dict, batch)
        probs  = torch.softmax(logits, dim=-1)

    print(f"  Logits : {logits.shape}  (beklenen: [4, 4])")
    print(f"  Probs  : {probs.shape}   (beklenen: [4, 4])")
    assert logits.shape == (4, 4)
    print("  Tum testler gecti!")
    return model


if __name__ == '__main__':
    run_full_test()