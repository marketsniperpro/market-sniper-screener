import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabase';
import { Signal } from '@/types/signal';

// GET /api/signals - Get all signals with optional filters
export async function GET(request: NextRequest) {
  const supabase = createServerClient();
  const searchParams = request.nextUrl.searchParams;

  // Query params
  const limit = parseInt(searchParams.get('limit') || '50');
  const offset = parseInt(searchParams.get('offset') || '0');
  const sector = searchParams.get('sector');
  const status = searchParams.get('status') || 'active';
  const minScore = parseInt(searchParams.get('minScore') || '0');
  const days = parseInt(searchParams.get('days') || '30');

  try {
    let query = supabase
      .from('signals')
      .select('*', { count: 'exact' })
      .gte('signal_date', new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0])
      .gte('fund_score', minScore)
      .order('signal_date', { ascending: false })
      .range(offset, offset + limit - 1);

    if (sector && sector !== 'all') {
      query = query.eq('sector', sector);
    }

    if (status && status !== 'all') {
      query = query.eq('status', status);
    }

    const { data, count, error } = await query;

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({
      signals: data as Signal[],
      total: count || 0,
    });
  } catch (err) {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
