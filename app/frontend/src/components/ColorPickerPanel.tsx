import { useEffect, useState } from 'react'
import { ColorPicker, Group, Paper, Text } from '@mantine/core'

interface ColorPickerPanelProps {
  onColorSelect: (hex: string) => void
  onActivate: () => void
  submitting: boolean
}

export function ColorPickerPanel({
  onColorSelect,
  onActivate,
  submitting,
}: ColorPickerPanelProps) {
  const [value, setValue] = useState('#000000')

  return (
    <Paper p="lg" withBorder>
      <Group justify="space-between" align="center" mb="md">
        <Text fw={600}>Pick a color</Text>
        <Text c="dimmed" size="sm">
          {value}
        </Text>
      </Group>
      <ColorPicker
        value={value}
        onChange={(v) => {
          if (v) {
            setValue(v)
            onActivate()
          }
        }}
        format="hex"
        channels={['hue', 'saturation', 'value']}
        swatches={['#e535ab', '#40c7ff', '#61ddaa', '#8494a1', '#94bcff', '#ffb648']}
        allowEmpty={false}
        hideSelectors
        shadowSize="0"
        shadowOffset={0}
        shadowColor="transparent"
      />
      <Group mt="md" justify="flex-end">
        <button
          style={{
            background: '#0070f3',
            color: 'white',
            border: 'none',
            padding: '10px 24px',
            borderRadius: 8,
            cursor: submitting ? 'not-allowed' : 'pointer',
            fontSize: 16,
            fontWeight: 600,
            opacity: submitting ? 0.6 : 1,
          }}
          disabled={submitting}
          onClick={() => onColorSelect(value)}
        >
          {submitting ? 'Submitting...' : 'Submit'}
        </button>
      </Group>
    </Paper>
  )
}
