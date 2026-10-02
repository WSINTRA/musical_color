import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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

function getSeenIds(): string[] {
  const raw = localStorage.getItem('seen_track_ids')
  if (!raw) return []
  return JSON.parse(raw)
}

function markSeen(trackId: string) {
  const seen = getSeenIds()
  if (!seen.includes(trackId)) {
    seen.push(trackId)
    localStorage.setItem('seen_track_ids', JSON.stringify(seen))
  }
}

export default function App() {
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null)
  const [mode, setMode] = useState<'instrumental' | 'lyrics'>('instrumental')
  const [selectionStartTime, setSelectionStartTime] = useState<number | null>(null)
  const queryClient = useQueryClient()

  const { data: tracks } = useQuery({
    queryKey: ['tracks'],
    queryFn: () => fetchTracks(getSeenIds()),
    staleTime: Infinity,
  })

  const submitMutation = useMutation({
    mutationFn: submitLabel,
    onSuccess: () => {
      if (currentTrack) {
        markSeen(currentTrack.track_id)
        setCurrentTrack(null)
        setSelectionStartTime(null)
        queryClient.invalidateQueries({ queryKey: ['tracks'] })
      }
    },
  })

  const handleNext = () => {
    const unselected = tracks?.find((t) => !getSeenIds().includes(t.track_id))
    if (unselected) {
      setCurrentTrack(unselected)
      setSelectionStartTime(null)
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

  if (!currentTrack && tracks && tracks.length === 0) {
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
        <Button size="lg" onClick={handleNext} disabled={!tracks || tracks.length === 0}>
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
          <LyricsDisplay
            trackId={currentTrack.track_id}
            sectionStart={currentTrack.section_start}
            sectionEnd={currentTrack.section_end}
          />
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
