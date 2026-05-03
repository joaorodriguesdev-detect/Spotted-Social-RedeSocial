"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import type { Post } from "@/types";

interface PostContextType {
  posts: Post[];
  addPost: (post: Post) => void;
  setPosts: (posts: Post[]) => void;
  userPosts: (userId: number) => Post[];
}

const PostContext = createContext<PostContextType | null>(null);

export function PostProvider({ children, initialPosts }: { children: ReactNode; initialPosts: Post[] }) {
  const [posts, setPosts] = useState<Post[]>(initialPosts);

  const addPost = useCallback((post: Post) => {
    setPosts((prev) => [post, ...prev]);
  }, []);

  // Escuta evento global disparado pelo CreatePostModal
  useEffect(() => {
    function handler(e: CustomEvent) {
      addPost(e.detail as Post);
    }
    window.addEventListener("new-post", handler as EventListener);
    return () => window.removeEventListener("new-post", handler as EventListener);
  }, [addPost]);

  const userPosts = useCallback((userId: number) => {
    return posts.filter((p) => p.user_id === userId && !p.is_anonymous);
  }, [posts]);

  return ( <PostContext.Provider value={{ posts, addPost, setPosts, userPosts }}>
      {children}
    </PostContext.Provider>
  );
}

export function usePosts(): PostContextType {
  const ctx = useContext(PostContext);
  if (!ctx) throw new Error("usePosts must be used within PostProvider");
  return ctx;
}

