import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// 대시보드는 읽기 전용(anon). RLS의 SELECT 정책으로만 접근한다.
export const supabase = createClient(url, anon);
