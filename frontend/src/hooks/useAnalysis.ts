import { useState, useCallback } from 'react';
import type { FullAnalysis, StreamEvent, AnalyzeResponse, ExampleEvent } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://host.docker.internal:8080';

export function useAnalysis() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FullAnalysis | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [stepMessage, setStepMessage] = useState<string>('');

  const analyze = useCallback(async (title: string, content: string = '') => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStep(0);

    try {
      const response = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title, content }),
      });

      const data: AnalyzeResponse = await response.json();

      if (!data.success) {
        throw new Error(data.error || '分析失败');
      }

      setResult(data.data!);
      return data.data!;
    } catch (err) {
      const message = err instanceof Error ? err.message : '未知错误';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const analyzeStream = useCallback(async (title: string, content: string = '') => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStep(0);

    const eventAnalysis: any = { direct_impacts: [] };
    const transmission: any = { transmission_chain: [], investment_signals: [] };
    const signals: any[] = [];

    try {
      const response = await fetch(`${API_BASE}/api/v1/analyze/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title, content }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: StreamEvent = JSON.parse(line.slice(6));

              if (event.step === 1) {
                setCurrentStep(1);
                setStepMessage('正在理解事件...');
                if (event.status === 'done') {
                  eventAnalysis.event_type = event.data.event_type;
                  eventAnalysis.core_entities = event.data.core_entities;
                  eventAnalysis.sentiment = event.data.sentiment;
                  eventAnalysis.event_intensity = event.data.event_intensity;
                  eventAnalysis.summary = event.data.summary;
                  eventAnalysis.direct_impacts = event.data.direct_impacts;
                }
              } else if (event.step === 2) {
                setCurrentStep(2);
                setStepMessage('正在分析产业链传导...');
                if (event.status === 'done') {
                  transmission.transmission_chain = event.data.transmission_chain;
                  transmission.affected_industries = event.data.affected_industries;
                  transmission.investment_signals = event.data.investment_signals;
                }
              } else if (event.step === 3) {
                setCurrentStep(3);
                setStepMessage('正在生成交易信号...');
                if (event.status === 'done') {
                  signals.push(...event.data);
                }
              } else if (event.step === 99) {
                setCurrentStep(99);
                setStepMessage('分析完成');
              }

              if (event.status === 'error') {
                setError(event.message || '分析出错');
              }
            } catch (e) {
              console.error('解析流事件失败:', e);
            }
          }
        }
      }

      if (!error) {
        const fullResult: FullAnalysis = {
          input_title: title,
          input_content: content,
          event_analysis: eventAnalysis,
          transmission: transmission,
          signals: signals,
          analysis_timestamp: new Date().toISOString(),
          processing_time_ms: 0,
        };
        setResult(fullResult);
        return fullResult;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '未知错误';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [error]);

  const clearResult = useCallback(() => {
    setResult(null);
    setError(null);
    setCurrentStep(0);
    setStepMessage('');
  }, []);

  return {
    loading,
    error,
    result,
    currentStep,
    stepMessage,
    analyze,
    analyzeStream,
    clearResult,
  };
}

export function useExamples() {
  const [examples, setExamples] = useState<ExampleEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchExamples = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/examples`);
      const data = await response.json();
      setExamples(data);
    } catch (err) {
      console.error('获取示例失败:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { examples, loading, fetchExamples };
}