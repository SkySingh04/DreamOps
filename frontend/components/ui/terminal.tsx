'use client';

import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { cn } from '@/lib/utils';

interface TerminalProps {
  className?: string;
  onCommand?: (command: string) => void;
  initialContent?: string[];
}

export interface TerminalHandle {
  writeln: (text: string) => void;
  clear: () => void;
}

export const Terminal = forwardRef<TerminalHandle, TerminalProps>(
  ({ className, onCommand, initialContent = [] }, ref) => {
    const [history, setHistory] = useState<string[]>([
      ...initialContent,
      'Connected to Kubernetes cluster: oncall-agent-eks',
      'Namespace: default',
      'Context: arn:aws:eks:ap-south-1:500489831186:cluster/oncall-agent-eks',
      '',
    ]);
    const [currentCommand, setCurrentCommand] = useState('');
    const [commandHistory, setCommandHistory] = useState<string[]>([]);
    const [historyIndex, setHistoryIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const terminalRef = useRef<HTMLDivElement>(null);

    useImperativeHandle(ref, () => ({
      writeln: (text: string) => {
        setHistory(prev => [...prev, text]);
      },
      clear: () => {
        setHistory([]);
      },
    }));

    useEffect(() => {
      if (terminalRef.current) {
        terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
      }
    }, [history]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (currentCommand.trim()) {
          const cmd = currentCommand.trim();
          
          // Add to history
          setHistory(prev => [...prev, `$ ${cmd}`]);
          setCommandHistory(prev => [...prev, cmd]);
          setHistoryIndex(-1);
          
          // Handle built-in commands
          if (cmd === 'clear') {
            setHistory([]);
          } else if (cmd === 'help') {
            setHistory(prev => [...prev,
              'Available commands:',
              '  kubectl get pods              - List all pods',
              '  kubectl get services          - List all services',
              '  kubectl logs <pod-name>       - Show pod logs',
              '  kubectl describe pod <name>   - Describe a pod',
              '  kubectl exec -it <pod> -- sh  - Shell into a pod',
              '  clear                         - Clear terminal',
              '  help                          - Show this help',
            ]);
          } else {
            // Send command to parent
            onCommand?.(cmd);
          }
          
          setCurrentCommand('');
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (commandHistory.length > 0 && historyIndex < commandHistory.length - 1) {
          const newIndex = historyIndex + 1;
          setHistoryIndex(newIndex);
          setCurrentCommand(commandHistory[commandHistory.length - 1 - newIndex]);
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIndex > 0) {
          const newIndex = historyIndex - 1;
          setHistoryIndex(newIndex);
          setCurrentCommand(commandHistory[commandHistory.length - 1 - newIndex]);
        } else if (historyIndex === 0) {
          setHistoryIndex(-1);
          setCurrentCommand('');
        }
      }
    };

    return (
      <div
        className={cn(
          'bg-gray-900 text-green-400 font-mono text-sm h-full overflow-hidden flex flex-col',
          className
        )}
        onClick={() => inputRef.current?.focus()}
      >
        <div
          ref={terminalRef}
          className="flex-1 overflow-y-auto p-4 space-y-1"
        >
          {history.map((line, index) => (
            <div key={index} className="whitespace-pre-wrap">
              {line}
            </div>
          ))}
          <div className="flex items-center">
            <span className="mr-2">$</span>
            <input
              ref={inputRef}
              type="text"
              value={currentCommand}
              onChange={(e) => setCurrentCommand(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent outline-none text-green-400"
              spellCheck={false}
              autoComplete="off"
              autoFocus
            />
          </div>
        </div>
      </div>
    );
  }
);

Terminal.displayName = 'Terminal';

export default Terminal;