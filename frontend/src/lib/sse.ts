// Reads a Server-Sent Events body, calling onEvent for each complete frame.
export async function readEvents(
  body: ReadableStream<Uint8Array>,
  onEvent: (name: string, data: unknown) => void,
) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const flush = () => {
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (!data.length) continue; // comment or keepalive
      let parsed: unknown;
      try {
        parsed = JSON.parse(data.join("\n"));
      } catch {
        continue; // skip a malformed frame rather than failing the stream
      }
      onEvent(name, parsed);
    }
  };
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      if (done) {
        buffer += "\n\n"; // a body ending without a blank line still has a last frame
        flush();
        return;
      }
      flush();
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}
