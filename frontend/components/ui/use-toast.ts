import * as React from "react"

type ToastProps = {
  title?: string
  description?: string
  variant?: "default" | "destructive"
}

type ToastContextType = {
  toast: (props: ToastProps) => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    // Return a mock toast function that logs to console if context not available
    return {
      toast: (props: ToastProps) => {
        console.log("Toast:", props)
      }
    }
  }
  return context
}

export { ToastContext, type ToastProps }