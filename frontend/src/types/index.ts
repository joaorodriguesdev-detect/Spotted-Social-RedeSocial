/**
 * ───────────────────────────────────────────────────────────────────────
 *  Spotted Social V2 – Tipos Compartilhados (TypeScript)
 *  ───────────────────────────────────────────────────────────────────────
 *  Interfaces espelhadas nos schemas Pydantic do backend FastAPI.
 *  Campos usam snake_case para bater com as respostas da API.
 * ───────────────────────────────────────────────────────────────────────
 */

// ═══════════════════════════════════════════════════════════════════════
//  USER
// ═══════════════════════════════════════════════════════════════════════

export interface User {
  id: number;
  username: string;
  name: string | null;
  email?: string | null;
  university?: string | null;
  bio: string | null;
  profile_pic: string | null;
  social_link?: string | null;
  is_admin: boolean;
  is_verified?: boolean;
  is_banned?: boolean;
  created_at: string | null;
  followers_count?: number;
  following_count?: number;
  posts_count?: number;
}

export interface AuthResponse {
  message?: string;
  user_id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
  is_admin: boolean;
  token?: string | null;
}

export interface UserProfile {
  id: number;
  username: string;
  name: string | null;
  university: string | null;
  bio: string | null;
  profile_pic: string | null;
  social_link: string | null;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string | null;
  followers_count: number;
  following_count: number;
  posts_count: number;
  recent_posts: Post[];
  active_coupons: CouponBrief[];
  is_owner: boolean;
  is_following: boolean;
}

// ═══════════════════════════════════════════════════════════════════════
//  POST (Feed)
// ═══════════════════════════════════════════════════════════════════════

export interface Post {
  id: number;
  content: string;
  media_url: string | null;
  media_urls?: string[];
  timestamp: string | null;
  likes: number;
  user_id: number | null;
  is_anonymous: boolean;
  liked_by_me: boolean;
  author_username: string | null;
  author_name: string | null;
  author_profile_pic: string | null;
  comment_count: number;
}

export interface PostCreatePayload {
  content: string;
  is_anonymous?: boolean;
  file?: File | null;
}

export interface FeedResponse {
  items: Post[];
  has_more: boolean;
  page?: number;
  limit?: number;
  total_count?: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMENT
// ═══════════════════════════════════════════════════════════════════════

export interface Comment {
  id: number;
  post_id: number;
  content: string;
  username: string;
  user_id: number | null;
  timestamp: string | null;
  is_edited: boolean;
}

export interface CommentCreatePayload {
  content: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  MURAL (Classified Ads)
// ═══════════════════════════════════════════════════════════════════════

export interface MuralPost {
  id: number;
  title: string;
  content: string;
  category: string;
  contact_info: string;
  timestamp: string | null;
  user_id: number;
  author_username: string | null;
  author_name: string | null;
  author_pic: string | null;
}

export interface MuralPostCreatePayload {
  title: string;
  content: string;
  category: string;
  contact_info: string;
}

export interface MuralPostUpdatePayload {
  title?: string;
  content?: string;
  category?: string;
  contact_info?: string;
}

export interface MuralListResponse {
  items: MuralPost[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  RECADO (Profile Wall Message)
// ═══════════════════════════════════════════════════════════════════════

export interface Recado {
  id: number;
  receiver_id: number;
  sender_name: string;
  content: string;
  timestamp: string | null;
}

export interface RecadoCreatePayload {
  content: string;
  anon_mode?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════
//  EVENT
// ═══════════════════════════════════════════════════════════════════════

export interface Event {
  id: number;
  title: string;
  description: string;
  event_date: string;
  location: string;
  category: string;
  media_url: string | null;
  created_at: string | null;
  user_id: number | null;
  creator_username: string | null;
  creator_name: string | null;
  creator_profile_pic: string | null;
}

export interface EventCreatePayload {
  title: string;
  description: string;
  event_date: string;
  location: string;
  category?: string;
  media_url?: string | null;
}

export interface EventListResponse {
  items: Event[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  CHAT / MESSAGEM
// ═══════════════════════════════════════════════════════════════════════

export interface ChatMessage {
  id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  media_url: string | null;
  created_at: string | null;
  all_read: boolean;
  is_mine: boolean;
}

export interface ConversationItem {
  conversation_id: number;
  other_user_id: number | null;
  other_username: string | null;
  other_name: string | null;
  other_profile_pic: string | null;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
  is_online: boolean;
}

export interface ChatHistory {
  conversation_id: number;
  other_user_id: number;
  other_username: string | null;
  other_name: string | null;
  other_profile_pic: string | null;
  messages: ChatMessage[];
  is_online: boolean;
}

// ═══════════════════════════════════════════════════════════════════════
//  NOTIFICATION
// ═══════════════════════════════════════════════════════════════════════

export interface Notification {
  id: number;
  user_id: number;
  sender_name: string | null;
  action_type: string | null;
  category: string;
  post_id: number | null;
  is_read: boolean;
  timestamp: string | null;
}

export interface NotificationsListResponse {
  items: Notification[];
  unread_count: number;
  total: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  COUPON
// ═══════════════════════════════════════════════════════════════════════

export interface Coupon {
  id: number;
  code: string;
  title: string;
  description: string | null;
  discount_percent: number;
  max_uses: number;
  current_uses: number;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  created_by_id: number;
}

export interface CouponBrief {
  id: number;
  code: string;
  title: string;
  discount_percent: number;
  is_active: boolean;
  current_uses: number;
  max_uses: number;
  expires_at: string | null;
}

export interface CouponCreatePayload {
  code: string;
  title: string;
  description?: string | null;
  discount_percent?: number;
  max_uses?: number;
  expires_at?: string | null;
}

// ═══════════════════════════════════════════════════════════════════════
//  FOLLOW / SOCIAL
// ═══════════════════════════════════════════════════════════════════════

export interface FollowStatus {
  is_following: boolean;
}

export interface FollowCounts {
  followers: number;
  following: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  ADMIN
// ═══════════════════════════════════════════════════════════════════════

export interface AdminStats {
  total_users: number;
  active_users: number;
  banned_users: number;
  online_users: number;
  new_users_today: number;
  posts_today: number;
  total_posts: number;
  active_coupons: number;
  pending_coupons: number;
}

export interface AuditLog {
  id: number;
  admin_id: number;
  action: string;
  target_id: number | null;
  target_type: string;
  details: string | null;
  timestamp: string | null;
  admin_username?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  GENERIC
// ═══════════════════════════════════════════════════════════════════════

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiErrorResponse {
  detail: string | Array<{ msg: string; [key: string]: unknown }>;
}

export type LikeResponse = {
  ok: boolean;
  liked: boolean;
  likes: number;
};

export type DeleteResponse = void;
