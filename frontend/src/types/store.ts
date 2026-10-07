export type StoreTab = 'products' | 'digital' | 'orders';

export interface ProductItem {
  id: string;
  creator_id: string;
  title: string;
  description?: string;
  price_inr: number;
  rating: number;
  image_url: string;
  is_digital: boolean;
  in_stock: boolean;
  inventory_count: number;
  badge?: string;
}

export interface CommunityPass {
  id: string;
  creator_id: string;
  title: string;
  price_inr: number; // 0 for ₹0 Free Pass
  interval: string; // e.g. "month"
  description: string;
  benefits: string[];
  is_active: boolean;
}

export type OrderStatus = 'PAID' | 'PROCESSING' | 'SHIPPED' | 'DELIVERED';

export interface OrderRecord {
  id: string;
  product_id: string;
  product_title: string;
  product_image: string;
  price_inr: number;
  quantity: number;
  total_amount_inr: number;
  status: OrderStatus;
  created_at: string;
}
