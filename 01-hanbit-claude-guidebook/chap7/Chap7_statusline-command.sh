#!/usr/bin/env bash
# Claude Code status line — 3-bar (ctx / 5h / 7d) + effort + worktree-aware
input=$(cat)

# --- Single jq pass: emit fixed-order values joined by 0x1F (Unit Separator) ---
# A non-whitespace delimiter so `read` preserves empty fields (git_worktree,
# wt_name, rate limits) instead of collapsing them the way a tab IFS would.
IFS=$'\037' read -r \
  model_name model_id \
  project_dir current_dir git_worktree wt_name \
  cost effort fast_mode session_name \
  ctx_pct rate_5h rate_7d \
  in_tok \
  <<EOF
$(echo "$input" | jq -j '
  [ (.model.display_name // .model.id // "?")
  , (.model.id // "")
  , (.workspace.project_dir // "")
  , (.workspace.current_dir // "")
  , (.workspace.git_worktree // "")
  , (.worktree.name // "")
  , (.cost.total_cost_usd // 0)
  , (.effort.level // "")
  , (.fast_mode // false)
  , (.session_name // "")
  , (.context_window.used_percentage // 0)
  , (.rate_limits.five_hour.used_percentage // "")
  , (.rate_limits.seven_day.used_percentage // "")
  , (.context_window.total_input_tokens // 0)
  ] | map(tostring) | join("")')
EOF

# --- Colors ---
RESET='\033[0m'; DIM='\033[2m'; BOLD='\033[1m'
C_GREEN='\033[32m'; C_YELLOW='\033[33m'; C_RED='\033[31m'
C_CYAN='\033[36m'; C_BLUE='\033[34m'; C_MAGENTA='\033[35m'; C_GREY='\033[90m'

# --- Project / worktree (project name stays; worktree shown once) ---
project=$(basename "$project_dir" 2>/dev/null)
[ -z "$project" ] || [ "$project" = "." ] && project=$(basename "$current_dir" 2>/dev/null)
cur_base=$(basename "$current_dir" 2>/dev/null)

worktree="$wt_name"
[ -z "$worktree" ] && worktree="$git_worktree"
# Fallback: current dir differs from project → treat as worktree/subdir label
[ -z "$worktree" ] && [ -n "$cur_base" ] && [ "$cur_base" != "$project" ] && worktree="$cur_base"

# --- Git branch ---
branch=""
if git -C "$current_dir" rev-parse --git-dir >/dev/null 2>&1; then
  branch=$(git -C "$current_dir" branch --show-current 2>/dev/null)
fi

# --- Progress bar helper: pct + base_color -> colored 8-block bar + pct ---
BAR_W=8
make_bar() {
  local pct="$1" base="$2" col
  pct=$(printf '%.0f' "$pct" 2>/dev/null); [ -z "$pct" ] && pct=0
  [ "$pct" -gt 100 ] && pct=100
  local filled=$(( (pct * BAR_W + 50) / 100 )); local empty=$(( BAR_W - filled ))
  # Escalate to warning colors near the limit; otherwise use the bar's base hue
  if   [ "$pct" -ge 90 ]; then col="$C_RED"
  elif [ "$pct" -ge 75 ]; then col="$C_YELLOW"
  else col="$base"; fi
  local bar=""; local i
  for ((i=0;i<filled;i++)); do bar+="▓"; done
  for ((i=0;i<empty;i++));  do bar+="░"; done
  printf '%b%s %d%%%b' "$col" "$bar" "$pct" "$RESET"
}

# --- Cost (flag fable when cost not yet computed) ---
cost_fmt=$(printf '$%.2f' "$cost" 2>/dev/null)
is_zero=$(awk -v c="$cost" 'BEGIN{print (c+0 < 0.005)?1:0}')
case "$model_id" in
  *fable*) [ "$is_zero" = "1" ] && [ "$in_tok" -gt 1000 ] 2>/dev/null && cost_fmt+=" ⚠" ;;
esac

# ================= Line 1 =================
line1="${BOLD}[$model_name]${RESET}"
[ "$fast_mode" = "true" ] && line1+=" ⚡"
[ -n "$project" ] && line1+=" 📁 $project"
[ -n "$worktree" ] && [ "$worktree" != "$project" ] && line1+=" ${C_MAGENTA}⑃ $worktree${RESET}"
# Show branch only if it isn't already conveyed by the worktree label
[ -n "$branch" ] && [ "$branch" != "$worktree" ] && line1+=" 🌿 $branch"
[ -n "$effort" ] && line1+=" ${DIM}|${RESET} ⚙ ${effort}"
line1+=" ${DIM}|${RESET} $cost_fmt"
[ -n "$session_name" ] && line1+=" ${DIM}✎ ${session_name}${RESET}"

# ================= Line 2 =================
line2="ctx $(make_bar "$ctx_pct" "$C_GREEN")"
[ -n "$rate_5h" ] && line2+="  ${C_GREY}5h${RESET} $(make_bar "$rate_5h" "$C_CYAN")"
[ -n "$rate_7d" ] && line2+="  ${C_GREY}7d${RESET} $(make_bar "$rate_7d" "$C_BLUE")"

printf "%b\n%b" "$line1" "$line2"
