export interface Track {
  track_id: string
  title: string
  artist: string
  album: string
  section_start: number
  section_end: number
}

export interface LabelInput {
  track_id: string
  color_hex: string
  mode: string
  time_to_select_ms: number
}

export interface LabelResponse {
  label_id: number
  status: string
}

export interface TrackPageParams {
  offset: number
  limit: number
}

export async function fetchTracks(params: TrackPageParams): Promise<Track[]> {
  const query = new URLSearchParams({
    offset: String(params.offset),
    limit: String(params.limit),
  })
  const res = await fetch(`/api/tracks?${query.toString()}`)
  if (!res.ok) throw new Error(`Failed to fetch tracks: ${res.status}`)
  return res.json()
}

export async function submitLabel(input: LabelInput): Promise<LabelResponse> {
  const res = await fetch('/api/labels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) throw new Error(`Failed to submit label: ${res.status}`)
  return res.json()
}

export async function fetchLyrics(trackId: string): Promise<string> {
  try {
    const res = await fetch(`/clips/${trackId}_lyrics.txt`)
    if (!res.ok) return ''
    return res.text()
  } catch {
    return ''
  }
}
