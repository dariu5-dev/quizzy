export function createTimer(totalSeconds, onTick, onExpire) {
  let remaining = totalSeconds;
  let intervalId = null;

  function format(secs) {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  function start() {
    onTick(format(remaining), remaining);
    intervalId = setInterval(() => {
      remaining -= 1;
      onTick(format(remaining), remaining);
      if (remaining <= 0) {
        clearInterval(intervalId);
        onExpire();
      }
    }, 1000);
  }

  function stop() {
    if (intervalId) clearInterval(intervalId);
  }

  function elapsed() {
    return totalSeconds - remaining;
  }

  return { start, stop, elapsed, format };
}
