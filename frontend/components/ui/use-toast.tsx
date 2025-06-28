"use client"

import { toast as sonnerToast } from "sonner"

export type ToastVariant = "default" | "destructive"

interface ToastProps {
  title?: string
  description?: string
  variant?: ToastVariant
  action?: React.ReactNode
}

export function toast({ title, description, variant = "default", action }: ToastProps) {
  const message = title || description || ""
  const descriptionText = title && description ? description : undefined

  switch (variant) {
    case "destructive":
      sonnerToast.error(message, {
        description: descriptionText,
        action,
      })
      break
    default:
      sonnerToast(message, {
        description: descriptionText,
        action,
      })
      break
  }
}

// For compatibility with components that expect a hook
export function useToast() {
  return { toast }
}