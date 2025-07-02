'use client';

import React, { useEffect, useState } from 'react';
import { useDemo } from '@/lib/demo/DemoContext';

interface AnimatedCursorProps {
  className?: string;
}

export function AnimatedCursor({ className = '' }: AnimatedCursorProps) {
  const { state } = useDemo();
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isClicking, setIsClicking] = useState(false);
  const [targetElement, setTargetElement] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!state.isActive) return;

    const currentStep = state.currentStep;
    const currentActionIndex = state.currentActionIndex;

    // Simulate cursor movement based on demo step
    const simulateCursorMovement = () => {
      let target: HTMLElement | null = null;

      // Define target elements based on current step
      switch (currentStep) {
        case 1: // Integrations step
          target = document.querySelector('[data-demo-target="integrations-page"]') as HTMLElement;
          break;
        case 2: // Trigger step
          target = document.querySelector('[data-demo-target="dashboard"]') as HTMLElement;
          break;
        case 3: // Analysis step
          target = document.querySelector('[data-demo-target="ai-analysis"]') as HTMLElement;
          break;
        case 4: // Resolution step
          target = document.querySelector('[data-demo-target="ai-resolution"]') as HTMLElement;
          break;
        default:
          target = document.body;
      }

      if (target) {
        const rect = target.getBoundingClientRect();
        const newX = rect.left + rect.width / 2;
        const newY = rect.top + rect.height / 2;
        
        setPosition({ x: newX, y: newY });
        setTargetElement(target);
        
        // Simulate click animation
        setIsClicking(true);
        setTimeout(() => setIsClicking(false), 200);
      }
    };

    const timer = setTimeout(simulateCursorMovement, 100);
    return () => clearTimeout(timer);
  }, [state.isActive, state.currentStep, state.currentActionIndex]);

  if (!state.isActive) return null;

  return (
    <div
      className={`fixed pointer-events-none z-[100] transition-all duration-500 ease-out ${className}`}
      style={{
        left: position.x - 12,
        top: position.y - 12,
        transform: isClicking ? 'scale(0.8)' : 'scale(1)',
      }}
    >
      {/* Cursor */}
      <div className="relative">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          className="drop-shadow-lg"
        >
          <path
            d="M3 3l7.5 18L13 13l8-8L3 3z"
            fill="white"
            stroke="black"
            strokeWidth="1"
          />
        </svg>
        
        {/* Click animation */}
        {isClicking && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-blue-500 rounded-full animate-ping opacity-75" />
          </div>
        )}
      </div>
    </div>
  );
}

interface ElementHighlightProps {
  selector?: string;
  className?: string;
}

export function ElementHighlight({ selector, className = '' }: ElementHighlightProps) {
  const { state } = useDemo();
  const [highlightedElement, setHighlightedElement] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!state.isActive || !selector) return;

    const element = document.querySelector(selector) as HTMLElement;
    if (element) {
      setHighlightedElement(element);
      
      // Add highlight class
      element.classList.add('demo-highlight');
      
      // Remove highlight after delay
      const timer = setTimeout(() => {
        element.classList.remove('demo-highlight');
        setHighlightedElement(null);
      }, 2000);

      return () => {
        clearTimeout(timer);
        element.classList.remove('demo-highlight');
      };
    }
  }, [state.isActive, selector, state.currentStep, state.currentActionIndex]);

  if (!state.isActive || !highlightedElement) return null;

  const rect = highlightedElement.getBoundingClientRect();

  return (
    <div
      className={`fixed pointer-events-none z-40 border-2 border-blue-500 bg-blue-500/10 rounded-lg animate-pulse ${className}`}
      style={{
        left: rect.left - 4,
        top: rect.top - 4,
        width: rect.width + 8,
        height: rect.height + 8,
      }}
    />
  );
}

// Global CSS for demo highlighting
export function DemoStyles() {
  return (
    <style jsx global>{`
      .demo-highlight {
        position: relative;
        z-index: 30;
      }
      
      .demo-highlight::before {
        content: '';
        position: absolute;
        inset: -4px;
        border: 2px solid #3b82f6;
        border-radius: 8px;
        background: rgba(59, 130, 246, 0.1);
        animation: demo-pulse 2s infinite;
        pointer-events: none;
        z-index: -1;
      }
      
      @keyframes demo-pulse {
        0%, 100% {
          opacity: 0.5;
          transform: scale(1);
        }
        50% {
          opacity: 1;
          transform: scale(1.02);
        }
      }
      
      .demo-typing {
        border-right: 2px solid #3b82f6;
        animation: demo-blink 1s infinite;
      }
      
      @keyframes demo-blink {
        0%, 50% { border-color: #3b82f6; }
        51%, 100% { border-color: transparent; }
      }
    `}</style>
  );
}