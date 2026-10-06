import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Button,
  Center,
  Container,
  Group,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { fetchTracks, submitLabel } from './lib/api'
import { AudioPlayer } from './components/AudioPlayer'
import { LyricsDisplay } from './components/LyricsDisplay'
import { ColorPickerPanel } from './components/ColorPickerPanel'
import type { Track } from './lib/api'

const PAGE_SIZE = 25

function loadSeenIds(): string[] {
  const raw = localStorage.getItem('seen_track_ids')
  if (!raw) return []
  return JSON.parse(raw)
}

function loadResumeOffset(): number {
  const raw = localStorage.getItem('resume_offset')
  if (!raw) return 0
  const value = Number(raw)
  return Number.isFinite(value) && value >= 0 ? value : 0
}

function persistProgress(seen: Set<string>, offset: number) {
  localStorage.setItem('seen_track_ids', JSON.stringify(Array.from(seen)))
  localStorage.setItem('resume_offset', String(offset))
}

export default function App() {
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null)
  const [mode, setMode] = useState<'instrumental' | 'lyrics'>('instrumental')
  const [selectionStartTime, setSelectionStartTime] = useState<number | null>(null)
  const [offset, setOffset] = useState<number>(loadResumeOffset())

  const [seen, setSeen] = useState<Set<string>>(new Set(loadSeenIds()))

  const { data: page } = useQuery({
    queryKey: ['tracks', offset],
    queryFn: () => fetchTracks({ offset, limit: PAGE_SIZE }),
    staleTime: Infinity,
  })

  const submitMutation = useMutation({
    mutationFn: submitLabel,
    onSuccess: () => {
      if (!currentTrack) return
      const next = new Set(seen)
      next.add(currentTrack.track_id)
      setSeen(next)
      persistProgress(next, offset)
      setCurrentTrack(null)
      setSelectionStartTime(null)
    },
  })

  const handleNext = () => {
    const unselected = (page ?? []).find((t) => !seen.has(t.track_id))
    if (unselected) {
      setCurrentTrack(unselected)
      setSelectionStartTime(null)
      return
    }
    if (page && page.length >= PAGE_SIZE) {
      setOffset(offset + PAGE_SIZE)
    }
  }

  const handleColorSelect = (hex: string) => {
    if (!currentTrack) return
    const timeMs = selectionStartTime ? Date.now() - selectionStartTime : 0
    setSelectionStartTime(null)
    submitMutation.mutate({
      track_id: currentTrack.track_id,
      color_hex: hex,
      mode,
      time_to_select_ms: timeMs,
    })
  }

  const handleToggleMode = () => {
    setMode((m) => (m === 'instrumental' ? 'lyrics' : 'instrumental'))
    setSelectionStartTime(null)
  }

  const hasUnseen = (page ?? []).some((t) => !seen.has(t.track_id))
  const done = page !== undefined && !hasUnseen && page.length < PAGE_SIZE

  if (!currentTrack && done) {
    return (
      <Center h="100vh">
        <Stack align="center" gap="md">
          <Title order={2}>All done!</Title>
          <Text c="dimmed">You've labeled all available tracks.</Text>
        </Stack>
      </Center>
    )
  }

  if (!currentTrack) {
    return (
      <Center h="100vh">
        <Button size="lg" onClick={handleNext} disabled={done}>
          Start
        </Button>
      </Center>
    )
  }

  return (
    <Container size="sm" py="xl">
      <Stack gap="xl">
        <Group justify="space-between" align="center">
          <div>
            <Title order={3}>{currentTrack.title}</Title>
            <Text c="dimmed">
              {currentTrack.artist} — {currentTrack.album}
            </Text>
          </div>
          <Button
            variant="outline"
            onClick={handleToggleMode}
            leftSection={
              <Text size="sm">{mode === 'instrumental' ? '♪' : '📝'}</Text>
            }
          >
            {mode === 'instrumental' ? 'Instrumental' : 'Lyrics'}
          </Button>
        </Group>

        {mode === 'instrumental' ? (
          <AudioPlayer
            src={`/clips/${currentTrack.track_id}_instrumental.mp3`}
          />
        ) : (
          <LyricsDisplay trackId={currentTrack.track_id} />
        )}

        <ColorPickerPanel
          onColorSelect={handleColorSelect}
          onActivate={() => setSelectionStartTime(Date.now())}
          submitting={submitMutation.isPending}
        />
      </Stack>
    </Container>
  )
}
