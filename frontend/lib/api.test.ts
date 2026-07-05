import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/lib/api";

afterEach(() => vi.restoreAllMocks());

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "x",
    json: async () => body,
  });
}

describe("api client", () => {
  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { items: [], cached: true }));
    const res = await api.getNews();
    expect(res.cached).toBe(true);
  });

  it("posts to /generate", async () => {
    const f = mockFetch(202, { episode_id: 1, status: "pending", created: true });
    vi.stubGlobal("fetch", f);
    await api.generate();
    expect(f).toHaveBeenCalledWith("/api/generate", expect.objectContaining({ method: "POST" }));
  });

  it("throws ApiError with message from error envelope", async () => {
    vi.stubGlobal("fetch", mockFetch(422, { error: { code: "bad", message: "nope" } }));
    await expect(api.getPreferences()).rejects.toMatchObject({
      constructor: ApiError,
      status: 422,
      message: "nope",
    });
  });
});
