import { createClient } from '@supabase/supabase-js';

// For client-side (browser) - uses anon key
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// For server-side (API routes) - can use service key if needed
export function createServerClient() {
  return createClient(
    process.env.SUPABASE_URL || supabaseUrl,
    process.env.SUPABASE_SERVICE_KEY || supabaseAnonKey
  );
}
