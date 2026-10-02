# Infrastructure: S3 cache and GitHub Actions role

`cloudformation.yaml` creates everything the weekly workflow needs in AWS:

- **A private S3 bucket** for `data/raw` and `data/processed`. All public access is blocked, objects are encrypted by default (SSE-S3), versioning is on, old versions expire after 30 days, and non-HTTPS requests are denied.
- **The GitHub OIDC identity provider** (`token.actions.githubusercontent.com`), so the workflow gets short-lived credentials and no AWS keys are stored in GitHub.
- **An IAM role** that only workflows in `gulsherassad/scout` running on `refs/heads/main` can assume. It can list the bucket and read and write its objects, nothing else (no delete, no other buckets or services).

Expected cost: a few cents a month (about 150 MB stored, one sync a week).

## Deploy (AWS console)

1. Sign in to the AWS console and set the region (top right) to **Canada (Central) ca-central-1**.
2. Open **IAM → Identity providers**. Note whether `token.actions.githubusercontent.com` is already listed. An account can have only one, so step 5 depends on it.
3. Open **CloudFormation → Stacks → Create stack → With new resources (standard)**.
4. Under **Prerequisite – Prepare template**, choose **Choose an existing template**. Under **Specify template**, choose **Upload a template file**, then **Choose file** and select `infra/cloudformation.yaml`. Click **Next**.
5. **Stack name:** `scout-pipeline`. Parameters:
   - `CreateOIDCProvider`: `true`, or `false` if the provider already existed in step 2.
   - `GitHubRepo` (`gulsherassad/scout`) and `GitHubBranch` (`main`): leave as they are.

   Click **Next**.
6. **Configure stack options:** leave the defaults. Click **Next**.
7. **Review:** at the bottom, tick **I acknowledge that AWS CloudFormation might create IAM resources**, then **Submit**.
8. Wait for the status `CREATE_COMPLETE` (about a minute), then open the **Outputs** tab and copy `BucketName` and `RoleArn`.

## Connect GitHub

1. In the repository on GitHub: **Settings → Secrets and variables → Actions → Variables tab → New repository variable**. Add two variables (they are not secrets: neither grants access on its own):
   - `AWS_ROLE_ARN` = the `RoleArn` output
   - `SCOUT_BUCKET` = the `BucketName` output
2. Push the workflow to `main`, then run it once by hand: **Actions → weekly pipeline → Run workflow** (branch `main`).

The first run starts with an empty bucket, so it downloads every match again (about 2,000 requests at 1.5 seconds each, roughly an hour; the job timeout is two hours). To skip that, upload your local data once with your own AWS credentials, not the role:

```bash
aws s3 sync data "s3://<BucketName>/data" --region ca-central-1
```

After that, the workflow runs every Tuesday at 06:00 UTC. GitHub disables scheduled workflows in a public repository after 60 days without commits; re-enable it under **Actions** if that happens.

## Tear down

1. **S3 → Buckets →** the scout bucket **→ Empty**. Type `permanently delete` to confirm; this removes all objects and all their versions. CloudFormation cannot delete a bucket that still has objects.
2. **CloudFormation → Stacks → `scout-pipeline` → Delete**. This removes the bucket, the role and, if this stack created it, the OIDC provider. If other workflows in your account use that provider, deploy with `CreateOIDCProvider = false` next time.
3. In GitHub, delete the two repository variables, or disable the workflow under **Actions → weekly pipeline → ⋯ → Disable workflow**.
