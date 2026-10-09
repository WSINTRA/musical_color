import { Paper, Stack, Text } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { fetchLyrics } from '../lib/api'

interface LyricsDisplayProps {
  trackId: string
}

const sectionMarker = '=== SECTION LYRICS ==='
const fullLyricsMarker = '=== FULL LYRICS ==='

function extractSectionLyrics(text: string): string[] {
  if (text.trim() === '') return []
  const start = text.indexOf(sectionMarker)
  const body = start >= 0 ? text.slice(start + sectionMarker.length) : text
  const end = body.indexOf(fullLyricsMarker)
  const section = end >= 0 ? body.slice(0, end) : body
  return section
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '' && !line.startsWith('#'))
}

export function LyricsDisplay({ trackId }: LyricsDisplayProps) {
  const { data: lines, isLoading } = useQuery({
    queryKey: ['lyrics', trackId],
    queryFn: async () => {
      const text = await fetchLyrics(trackId)
      return extractSectionLyrics(text)
    },
    staleTime: Infinity,
  })

  if (isLoading) {
    return (
      <Paper p='xl' w='100%'>
        <Text c='dimmed' ta='center'>
          Loading lyrics...
        </Text>
      </Paper>
    )
  }

  if (!lines || lines.length === 0) {
    return (
      <Paper p='xl' w='100%'>
        <Text c='dimmed' ta='center'>
          No lyrics available for this section.
        </Text>
      </Paper>
    )
  }

  return (
    <Paper p='xl' w='100%'>
      <Stack gap={4}>
        {lines.map((line, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: static, non-reorderable lyrics list
          <Text key={i} size='lg' fw={500} lineClamp={1}>
            {line}
          </Text>
        ))}
      </Stack>
    </Paper>
  )
}
