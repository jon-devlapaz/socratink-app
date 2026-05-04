-- 1. Create the feedback table
CREATE TABLE IF NOT EXISTS public.feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID DEFAULT auth.uid(), -- Link to auth.users if logged in
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'imported', 'dismissed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Enable Row Level Security
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- 3. Grant table access; RLS policies below still decide which rows/actions
-- each role may use.
GRANT INSERT ON public.feedback TO anon, authenticated;
GRANT SELECT, UPDATE, DELETE ON public.feedback TO authenticated;

-- 4. Replace feedback policies idempotently.
-- Keep INSERT isolated from admin triage. A FOR ALL admin policy with a
-- auth.users lookup is evaluated during INSERT and blocks public feedback with
-- "permission denied for table users".
DROP POLICY IF EXISTS "Allow feedback submission for everyone" ON public.feedback;
DROP POLICY IF EXISTS "Allow admin triage" ON public.feedback;
DROP POLICY IF EXISTS "Allow admin feedback select" ON public.feedback;
DROP POLICY IF EXISTS "Allow admin feedback update" ON public.feedback;
DROP POLICY IF EXISTS "Allow admin feedback delete" ON public.feedback;

-- Drop any other dashboard-created or manually renamed policies so stale INSERT
-- constraints cannot continue to reject feedback.
DO $$
DECLARE
  policy_record RECORD;
BEGIN
  FOR policy_record IN
    SELECT policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'feedback'
  LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS %I ON public.feedback',
      policy_record.policyname
    );
  END LOOP;
END $$;

-- 5. Policy: Allow anyone to INSERT feedback (authenticated users and guests).
CREATE POLICY "Allow feedback submission for everyone"
ON public.feedback
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- 6. Policy: Allow only the admin to triage feedback.
-- Replace the email with your admin email if different.
-- Use auth.jwt() instead of querying auth.users; anon/authenticated roles do not
-- have direct SELECT permission on auth.users.
CREATE POLICY "Allow admin feedback select"
ON public.feedback
FOR SELECT
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'jonathan10620@gmail.com'
);

CREATE POLICY "Allow admin feedback update"
ON public.feedback
FOR UPDATE
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'jonathan10620@gmail.com'
)
WITH CHECK (
  auth.jwt() ->> 'email' = 'jonathan10620@gmail.com'
);

CREATE POLICY "Allow admin feedback delete"
ON public.feedback
FOR DELETE
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'jonathan10620@gmail.com'
);
