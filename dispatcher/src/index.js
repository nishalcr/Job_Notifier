/**
 * Triggers the notifier GitHub Actions workflow via workflow_dispatch.
 * Runs on the cron schedule in wrangler.jsonc.
 */

async function dispatchWorkflow(env) {
  const url = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW}/dispatches`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type": "application/json",
      "User-Agent": "job-notifier-dispatcher",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: env.GITHUB_REF }),
  });

  if (response.status !== 204) {
    const body = await response.text();
    throw new Error(`GitHub dispatch failed: ${response.status} ${body}`);
  }
}

export default {
  async scheduled(controller, env, ctx) {
    if (!env.GITHUB_TOKEN) {
      throw new Error("GITHUB_TOKEN secret is not set");
    }
    await dispatchWorkflow(env);
    console.log(`Dispatched ${env.GITHUB_WORKFLOW} on ${env.GITHUB_REPO}@${env.GITHUB_REF}`);
  },

  async fetch() {
    return new Response("Not found", { status: 404 });
  },
};
