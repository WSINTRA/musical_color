import { useQuery } from '@tanstack/react-query'
import { Paper, Text, Stack } from '@mantine/core'
import { fetchLyrics } from '../lib/api'

interface LyricsDisplayProps {
  trackId: string
  sectionStart: number
  sectionEnd: number
}

export function LyricsDisplay({ trackId }: LyricsDisplayProps) {
  const { data: lyrics, isLoading } = useQuery({
    queryKey: ['lyrics', trackId],
    queryFn: () => fetchLyrics(trackId),
    staleTime: Infinity,
  })

  if (isLoading) {
    return (
      <Paper p="xl" w="100%">
        <Text c="dimmed" ta="center">Loading lyrics...</Text>
      </Paper>
    )
  }

  if (!lyrics || lyrics.trim() === '') {
    return (
      <Paper p="xl" w="100%">
        <Text c="dimmed" ta="center">No lyrics available for this section.</Text>
      </Paper>
    )
  }

  const lines = lyrics
    .split('\n')
    .filter((l) => l.trim() !== '' && !l.startsWith('['))
    .map((l) => l.replace(/^\[\d+:\d+(\.\d+)?\]\s*/, ''))
    .filter((l) => l.trim() !== '')

  return (
    <Paper p="xl" w="100%">
      <Stack gap={4}>
        {lines.map((line, i) => (
          <Text key={i} size="lg" fw={500} lineClamp={1}>
            {line}
          </Text>
        ))}
      </Stack>
    </Paper>
  )
}
