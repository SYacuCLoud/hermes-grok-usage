import { cn, haptic, host, Tip, useQuery } from '@hermes/plugin-sdk'
import { jsx } from 'react/jsx-runtime'

const ID = 'grok-usage'

function fmtReset(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export default {
  id: ID,
  name: 'Grok Usage',
  register(ctx) {
    function Chip() {
      const q = useQuery({
        queryKey: [ID, 'usage'],
        queryFn: () => ctx.rest('/usage'),
        refetchInterval: 120000,
        retry: 1,
      })
      const data = q.data
      const used = data && data.ok ? data.used_percent : null
      const label = used == null ? 'Grok —' : `Grok ${Math.round(used)}%`
      const tip = !data
        ? 'Grok weekly usage'
        : data.ok
          ? `${data.period} ${Math.round(data.used_percent)}% · reset ${fmtReset(data.resets_at)}`
          : data.error === 'no_auth'
            ? 'xAI login missing'
            : 'Usage unavailable — restart Hermes if this is the first load'
      const hot = used != null && used >= 80
      return jsx(Tip, {
        label: tip,
        children: jsx('button', {
          type: 'button',
          className: cn(
            'inline-flex h-full items-center px-1.5 text-[0.6875rem] transition-colors',
            'hover:bg-(--chrome-action-hover)',
            hot ? 'text-(--ui-accent)' : 'text-(--ui-text-tertiary) hover:text-foreground'
          ),
          onClick: () => {
            haptic('tap')
            ctx.os.openExternal('https://grok.com')
          },
          children: label,
        }),
      })
    }

    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 126,
      render: () => jsx(Chip, {}),
    })
  },
}
