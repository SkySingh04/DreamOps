'use client';

import React, { useState, useEffect } from 'react';

interface TypewriterEffectProps {
  text: string;
  speed?: number;
  delay?: number;
  onComplete?: () => void;
  className?: string;
}

export function TypewriterEffect({
  text,
  speed = 50,
  delay = 0,
  onComplete,
  className = ''
}: TypewriterEffectProps) {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isStarted, setIsStarted] = useState(false);

  useEffect(() => {
    const startTimer = setTimeout(() => {
      setIsStarted(true);
    }, delay);

    return () => clearTimeout(startTimer);
  }, [delay]);

  useEffect(() => {
    if (!isStarted || currentIndex >= text.length) {
      if (currentIndex >= text.length && onComplete) {
        onComplete();
      }
      return;
    }

    const timer = setTimeout(() => {
      setDisplayText(text.slice(0, currentIndex + 1));
      setCurrentIndex(currentIndex + 1);
    }, speed);

    return () => clearTimeout(timer);
  }, [currentIndex, text, speed, isStarted, onComplete]);

  return (
    <span className={`demo-typing ${className}`}>
      {displayText}
    </span>
  );
}

interface TypewriterFormProps {
  fields: Array<{
    selector: string;
    value: string;
    delay?: number;
  }>;
  onComplete?: () => void;
  isActive?: boolean;
}

export function TypewriterForm({ fields, onComplete, isActive = true }: TypewriterFormProps) {
  const [currentFieldIndex, setCurrentFieldIndex] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);

  useEffect(() => {
    if (!isActive || isCompleted || currentFieldIndex >= fields.length) {
      if (currentFieldIndex >= fields.length && !isCompleted && onComplete) {
        setIsCompleted(true);
        onComplete();
      }
      return;
    }

    const currentField = fields[currentFieldIndex];
    const element = document.querySelector(currentField.selector) as HTMLInputElement;
    
    if (element) {
      // Focus the element
      element.focus();
      
      // Add typing class for visual effect
      element.classList.add('demo-typing');
      
      // Simulate typing
      let currentValue = '';
      let charIndex = 0;
      
      const typeChar = () => {
        if (charIndex < currentField.value.length) {
          currentValue += currentField.value[charIndex];
          element.value = currentValue;
          
          // Dispatch input event to trigger React state updates
          element.dispatchEvent(new Event('input', { bubbles: true }));
          
          charIndex++;
          setTimeout(typeChar, 100);
        } else {
          // Remove typing class
          element.classList.remove('demo-typing');
          element.blur();
          
          // Move to next field after a delay
          setTimeout(() => {
            setCurrentFieldIndex(currentFieldIndex + 1);
          }, 500);
        }
      };
      
      // Start typing after field delay
      setTimeout(typeChar, currentField.delay || 0);
    } else {
      // If element not found, skip to next field
      setTimeout(() => {
        setCurrentFieldIndex(currentFieldIndex + 1);
      }, 100);
    }
  }, [currentFieldIndex, fields, isActive, isCompleted, onComplete]);

  return null; // This component doesn't render anything visible
}