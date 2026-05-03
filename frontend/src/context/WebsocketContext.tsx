"use client"

import { createContext, type ReactNode } from "react";

export interface WebsocketValue {
  heart: any;
}

interface WebsocketContextValue {}

export const WebsocketContext = createContext<WebsocketContextValue | undefined>(undefined);

export function WebsocketProvider({ children }: { children: ReactNode }) {

  const value: WebsocketValue = {
    heart: true,
  };

  return <WebsocketContext.Provider value={value}>{children}</WebsocketContext.Provider>;
}

