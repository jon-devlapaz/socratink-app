-- Auth-bound learner continuity: one JSONB blob per identified user.
-- Packet 1 stores raw learnops_concepts + socratink:training:v1:* payloads.
-- Due-for-spaced is derived client-side from training evidence (18h rule).

CREATE TABLE IF NOT EXISTS public.learner_state (
    user_id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    schema_version INTEGER NOT NULL DEFAULT 1,
    concepts JSONB NOT NULL DEFAULT '[]'::jsonb,
    training JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.learner_state ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE ON public.learner_state TO authenticated;

DROP POLICY IF EXISTS "learner_state_select_own" ON public.learner_state;
DROP POLICY IF EXISTS "learner_state_insert_own" ON public.learner_state;
DROP POLICY IF EXISTS "learner_state_update_own" ON public.learner_state;

CREATE POLICY "learner_state_select_own"
ON public.learner_state
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "learner_state_insert_own"
ON public.learner_state
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "learner_state_update_own"
ON public.learner_state
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
