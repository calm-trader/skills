#!/bin/bash
# R34 TradingView tab watchdog.
# Root cause it solves: a tab created by the Claude-in-Chrome MCP is never the ACTIVE tab,
# so document.hidden stays true, so TradingView never sizes its canvases (backing store
# stuck at 300x150) and the chart never paints. Fix = make the operator's TV tab active.
#
# Rule: the operator's tab is always the MOST RECENTLY created one, which Chrome appends
# at the highest index. So: keep only the LAST tradingview.com/chart tab in each window,
# close older duplicates (they are leftovers from earlier dispatches), and activate it.
# Does NOT steal application focus (no `activate`); it only sets the active tab index.
SENTINEL=/tmp/tv-tab-watchdog.on
LOG=/tmp/tv-tab-watchdog.log
touch "$SENTINEL"
echo "$(date '+%H:%M:%S') watchdog v2 started (targets LAST tv chart tab)" >> "$LOG"
while [ -f "$SENTINEL" ]; do
  osascript <<'EOF' 2>&1 | grep -v '^$' >> "$LOG"
tell application "Google Chrome"
  if (count of windows) is 0 then return ""
  set msg to ""
  repeat with w in windows
    try
      if minimized of w then set minimized of w to false
      -- find indices of all TradingView chart tabs
      set idxs to {}
      set n to count of tabs of w
      repeat with i from 1 to n
        if (URL of tab i of w) contains "tradingview.com/chart" then set end of idxs to i
      end repeat
      if (count of idxs) > 0 then
        set target to item (count of idxs) of idxs   -- the newest one
        -- close older duplicates, highest-first so indices stay valid
        if (count of idxs) > 1 then
          repeat with k from ((count of idxs) - 1) to 1 by -1
            set victim to item k of idxs
            close tab victim of w
            set target to target - 1
            set msg to msg & "closed stale tv tab " & victim & "; "
          end repeat
        end if
        if (active tab index of w) is not target then
          set active tab index of w to target
          set msg to msg & "activated tab " & target
        end if
      end if
    end try
  end repeat
  return msg
end tell
EOF
  sleep 4
done
echo "$(date '+%H:%M:%S') watchdog stopped" >> "$LOG"
