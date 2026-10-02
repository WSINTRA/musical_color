import { useRef, useState } from 'react'
import { Button, Center, Group, Text } from '@mantine/core'

interface AudioPlayerProps {
  src: string
}

export function AudioPlayer({ src }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)

  const toggle = () => {
    const audio = audioRef.current
    if (!audio) return
    if (playing) {
      audio.pause()
    } else {
      audio.currentTime = 0
      audio.play()
    }
  }

  return (
    <Center>
      <Group align="center" gap="md" w="100%">
        <Button
          variant="filled"
          size="xl"
          fw="bold"
          style={{ width: 64, height: 64, borderRadius: '50%' }}
          onClick={toggle}
          aria-label={playing ? 'Pause' : 'Play'}
        >
          {playing ? '❚❚' : '▶'}
        </Button>
        <div style={{ flex: 1 }}>
          <audio
            ref={audioRef}
            src={src}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            style={{ display: 'none' }}
          />
          <Text size="sm" c="dimmed">
            {playing ? 'Playing...' : 'Click play to listen'}
          </Text>
        </div>
      </Group>
    </Center>
  )
}
