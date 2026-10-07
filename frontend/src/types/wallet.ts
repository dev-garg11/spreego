export interface KPIMetric {
  label: string;
  value: string;
  growth_percent: number;
  is_positive: boolean;
}

export interface TrendDataPoint {
  day: string;
  views: number;
  formatted_views: string;
}

export interface TopPerformingItem {
  rank: number;
  title: string;
  views_display: string;
  likes_display: string;
  thumbnail_url: string;
}

export interface WalletSummary {
  available_balance_inr: number;
  pending_payout_inr: number;
  currency: string;
  upi_id?: string;
}

export interface PayoutRequestPayload {
  amount: number;
  upi_id: string;
}
