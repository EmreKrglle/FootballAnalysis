const BASE_URL = "http://127.0.0.1:8000";

export const getMatches = () =>
  fetch(`${BASE_URL}/matches`).then(res => res.json());

export const getEvents = (matchId) =>
  fetch(`${BASE_URL}/matches/${matchId}/events`).then(res => res.json());

export const getFreezeFrames = (eventId) =>
  fetch(`${BASE_URL}/events/${eventId}/freeze-frames`).then(res => res.json());

export const getMatchStats = (matchId) =>
  fetch(`${BASE_URL}/matches/${matchId}/stats`).then(res => res.json());

export const getLineup = (matchId) =>
  fetch(`${BASE_URL}/matches/${matchId}/lineup`).then(res => res.json());

export const getPlayerStats = (matchId, playerId) =>
  fetch(`${BASE_URL}/matches/${matchId}/player/${playerId}/stats`).then(res => res.json());