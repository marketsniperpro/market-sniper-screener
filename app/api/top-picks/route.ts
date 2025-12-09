import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabase';
import { Signal } from '@/types/signal';

// GET /api/top-picks - Get highest quality recent signals
export async function GET(request: NextRequest) {
  const supabase = createServerClient();
  const searchParams = request.nextUrl.searchParams;

  const limit = parseInt(searchParams.get('limit') || '10');
  const minScore = parseInt(searchParams.get('minScore') || '8');
  const days = parseInt(searchParams.get('days') || '90');

  try {
    const { data, error } = await supabase
      .from('signals')
      .select('*')
      .gte('fund_score', minScore)
      .gte('signal_date', new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0])
      .order('fund_score', { ascending: false })
      .order('signal_date', { ascending: false })
      .limit(limit);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({
      picks: data as Signal[],
    });
  } catch (err) {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
