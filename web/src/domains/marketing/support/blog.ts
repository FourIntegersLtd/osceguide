export interface Blog {
  id: string;
  blog_id: string;
  title: string;
  content: string;
  updated_at?: string;
  created_at: string;
  approved: boolean;
  url?: string;
}
