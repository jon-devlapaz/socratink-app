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

-- 3. Policy: Allow anyone to INSERT feedback (authenticated and guests)
-- This allows both 'anon' and 'authenticated' roles to submit.
-- Note: 'true' as the CHECK allows both anonymous (anon) and logged-in (authenticated) roles to post.
CREATE POLICY "Allow feedback submission for everyone" 
ON public.feedback 
FOR INSERT 
WITH CHECK (true);

-- 4. Policy: Allow only the admin to SELECT or UPDATE feedback
-- Replace the email with your admin email if different.
CREATE POLICY "Allow admin triage" 
ON public.feedback 
FOR ALL 
USING (
  (SELECT email FROM auth.users WHERE id = auth.uid()) = 'jonathan10620@gmail.com'
);
