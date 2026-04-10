-- Run this in Supabase SQL Editor (https://supabase.com/dashboard/project/husdhmaijvughqezlmjt/sql)

-- Usage tracking table
CREATE TABLE IF NOT EXISTS public.usage (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL,
  email TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_usage_user_id ON public.usage(user_id);

-- Enable RLS
ALTER TABLE public.usage ENABLE ROW LEVEL SECURITY;

-- Allow the service role to read/write (backend uses service role key)
CREATE POLICY "Service role full access" ON public.usage
  FOR ALL USING (true) WITH CHECK (true);

-- Sessions table for persistence
CREATE TABLE IF NOT EXISTS public.sessions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL,
  name TEXT NOT NULL,
  markdown TEXT,
  concept_groups JSONB DEFAULT '[]',
  verification_report JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);

ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- Users can only see their own sessions
CREATE POLICY "Users read own sessions" ON public.sessions
  FOR SELECT USING (auth.uid() = user_id);

-- Service role can insert (backend saves after pipeline)
CREATE POLICY "Service role insert sessions" ON public.sessions
  FOR INSERT WITH CHECK (true);

-- Users can delete their own sessions
CREATE POLICY "Users delete own sessions" ON public.sessions
  FOR DELETE USING (auth.uid() = user_id);

-- User profiles table (quiz answers + display settings)
CREATE TABLE IF NOT EXISTS public.user_profiles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE,
  display_name TEXT,
  avatar_color TEXT DEFAULT '#FF6B35',
  study_program TEXT,      -- medicine, nursing, pharmacy, dentistry, other
  study_year TEXT,          -- 1st year, 2nd year, 3rd year, 4th year+
  frustration TEXT,         -- biggest lecture frustration
  referral_source TEXT,     -- friend, tiktok, google, other
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can read/update their own profile
CREATE POLICY "Users read own profile" ON public.user_profiles
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users update own profile" ON public.user_profiles
  FOR UPDATE USING (auth.uid() = user_id);

-- Service role can insert/upsert (backend saves after quiz)
CREATE POLICY "Service role manage profiles" ON public.user_profiles
  FOR ALL USING (true) WITH CHECK (true);
