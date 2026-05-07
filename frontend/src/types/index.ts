// API 类型定义
export interface DirectImpact {
  industry: string;
  impact_direction: "利好" | "利空" | "中性";
  impact_magnitude: "高" | "中" | "低";
  impact_score: number;
}

export interface TransmissionStep {
  step: number;
  from_industry: string;
  to_industry: string;
  relation_type: string;
  transmission_rate: number;
  time_lag_days: number;
  impact_magnitude: "高" | "中" | "低";
  impact_score: number;
  description: string;
}

export interface InvestmentSignal {
  industry: string;
  signal: "做多" | "做空";
  confidence: number;
  reasoning: string;
}

export interface EventAnalysis {
  event_type: string;
  core_entities: string[];
  sentiment: number;
  event_intensity: "高" | "中" | "低";
  summary: string;
  direct_impacts: DirectImpact[];
}

export interface TransmissionChain {
  transmission_chain: TransmissionStep[];
  affected_industries: string[];
  investment_signals: InvestmentSignal[];
}

export interface BacktestReference {
  has_historical_reference: boolean;
  best_match?: {
    event_id: string;
    title: string;
    date: string;
    similarity_score: number;
  };
  adjusted_confidence: number;
  original_confidence: number;
  confidence_change: number;
  historical_win_rate: number;
  backtest_evaluation?: {
    is_reliable: boolean;
    expected_signal: string;
    matched_factors: string[];
    unmatched_factors: string[];
    actual_outcome: string;
  };
  recommendation: string;
  similar_events_count: number;
}

export interface StockSignal {
  stock_code: string;
  stock_name: string;
  signal_type: "BUY" | "SELL" | "HOLD";
  confidence: number;
  impact_score: number;
  chain_depth: number;
  entry_rationale: string;
  risk_factors: string[];
  related_stocks: string[];
  backtest_reference?: BacktestReference;
}

export interface FullAnalysis {
  input_title: string;
  input_content: string;
  event_analysis: EventAnalysis;
  transmission: TransmissionChain;
  signals: StockSignal[];
  analysis_timestamp: string;
  processing_time_ms: number;
}

export interface AnalyzeResponse {
  success: boolean;
  data?: FullAnalysis;
  error?: string;
  cached: boolean;
  degradation_message?: string;
}

export interface StreamEvent {
  step: number;
  status: "analyzing" | "done" | "error";
  message?: string;
  data?: any;
}

export interface ExampleEvent {
  title: string;
  content: string;
  category: string;
}