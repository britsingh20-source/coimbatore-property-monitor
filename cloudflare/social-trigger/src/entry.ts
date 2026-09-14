import worker, { type Env } from "./index";

/**
 * Thin production wrapper around the existing worker.
 *
 * Telegram retries the same webhook update whenever our endpoint returns 5xx.
 * The underlying worker already sends a useful Telegram warning when GitHub
 * dispatch fails, so returning 5xx only creates duplicate warning spam.
 * Normalize POST failures to HTTP 200 after the worker has handled/notified the
 * failure. Queue failures are intentionally left unchanged so R2 events retain
 * their retry semantics.
 */
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const response = await worker.fetch(request, env);

    if (request.method === "POST" && response.status >= 500) {
      console.error(
        `Telegram webhook handled with upstream status ${response.status}; returning 200 to stop Telegram replay.`,
      );
      return new Response("ok", { status: 200 });
    }

    return response;
  },

  async queue(batch: MessageBatch, env: Env, ctx: ExecutionContext): Promise<void> {
    await worker.queue(batch as any, env);
  },
} satisfies ExportedHandler<Env>;
