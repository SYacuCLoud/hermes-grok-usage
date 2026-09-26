import { cn, haptic, host, Tip, useQuery, useValue } from '@hermes/plugin-sdk'
import { jsx } from 'react/jsx-runtime'

const ID = 'grok-usage'

// model slug -> which account's usage to show. Unknown models fall back to Grok.
const FAMILIES = {
  chatgpt: { label: 'GPT', url: 'https://chatgpt.com/codex/settings/usage', auth: 'ChatGPT login missing' },
  claude: { label: 'Claude', url: 'https://claude.ai/settings/usage', auth: 'Claude login missing' },
  grok: { label: 'Grok', url: 'https://grok.com', auth: 'xAI login missing' },
}

function familyOf(model) {
  const m = String(model || '').toLowerCase()
  if (/claude|opus|sonnet|haiku/.test(m)) return 'claude'
  if (/gpt|codex|(^|[^a-z])o[134]([^a-z0-9]|$)/.test(m)) return 'chatgpt'
  return 'grok'
}

function fmtReset(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function remainingOf(data) {
  if (!data || !data.ok) return null
  if (typeof data.left_percent === 'number' && Number.isFinite(data.left_percent)) {
    return data.left_percent
  }
  if (typeof data.used_percent === 'number' && Number.isFinite(data.used_percent)) {
    return 100 - data.used_percent
  }
  return null
}

function tipOf(fam, data, remaining) {
  if (!data) return `${fam.label} usage remaining`
  if (data.ok && remaining != null) {
    const rows = Array.isArray(data.windows) && data.windows.length
      ? data.windows.map(w => `${w.label} ${Math.round(100 - w.used_percent)}% (reset ${fmtReset(w.resets_at)})`)
      : [`${data.period} ${Math.round(remaining)}% remaining · reset ${fmtReset(data.resets_at)}`]
    return [data.plan ? `${fam.label} ${data.plan}` : null, ...rows].filter(Boolean).join(' · ')
  }
  if (data.error === 'no_auth') return fam.auth
  if (data.error === 'no_oauth') return `${fam.label}: plan limits need subscription (OAuth) login, not an API key`
  if (data.error === 'auth_refresh_failed') return 'xAI token refresh failed'
  return 'Usage unavailable — restart Hermes if this is the first load'
}

export default {
  id: ID,
  name: 'Grok Usage',
  register(ctx) {
    function Chip() {
      const kind = familyOf(useValue(host.state.model))
      const fam = FAMILIES[kind]
      const q = useQuery({
        queryKey: [ID, 'usage', kind],
        queryFn: () => ctx.rest(`/usage?provider=${kind}`),
        refetchInterval: 120000,
        retry: 1,
      })
      const data = q.data
      const remaining = remainingOf(data)
      const label = remaining == null ? `${fam.label} —` : `${fam.label} ${Math.round(remaining)}%`
      const warning = remaining != null && remaining <= 20
      return jsx(Tip, {
        label: tipOf(fam, data, remaining),
        children: jsx('button', {
          type: 'button',
          className: cn(
            'inline-flex h-full items-center px-1.5 text-[0.6875rem] transition-colors',
            'hover:bg-(--chrome-action-hover)',
            warning ? 'text-(--ui-accent)' : 'text-(--ui-text-tertiary) hover:text-foreground'
          ),
          onClick: () => {
            haptic('tap')
            ctx.os.openExternal(fam.url)
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
