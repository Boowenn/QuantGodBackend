//+------------------------------------------------------------------+
//|                                         QuantGod_MultiStrategy.mq5 |
//|                              QuantGod MT5 Migration Skeleton      |
//+------------------------------------------------------------------+
#property copyright "QuantGod"
#property link      "https://github.com/Boowenn/MT4"
#property version   "3.17"
#property strict

#include <Trade/Trade.mqh>

input string DashboardBuild      = "QuantGod-v3.17-mt5-startup-entry-guard";
input string Watchlist           = "USDJPY";
input string PreferredSymbolSuffix = "AUTO";
input bool   ShadowMode          = true;
input bool   ReadOnlyMode        = true;
input int    RefreshIntervalSec  = 5;
input int    ClosedTradeLimit    = 50;
input int    HistoryLookbackDays = 30;
input bool   EnablePilotAutoTrading   = false;
input bool   EnablePilotStartupEntryGuard = true;
input int    PilotStartupEntryMinWaitMinutes = 15;
input bool   PilotStartupEntryWaitNextH1Bar = true;
input bool   EnablePilotMA            = true;
input bool   EnablePilotRsiH1Candidate = true;
input bool   EnablePilotRsiH1Live      = false;
input ENUM_TIMEFRAMES PilotRsiTimeframe = PERIOD_H1;
input int    PilotRsiPeriod           = 2;
input int    PilotRsiOverbought       = 85;
input int    PilotRsiOversold         = 15;
input double PilotRsiCrossbackThreshold = 0.0;
input double PilotRsiBandTolerancePct = 0.006;
input double PilotRsiATRMultiplierSL  = 1.5;
input bool   EnablePilotRsiFastExitProtect = true;
input int    PilotRsiProtectMinAgeMinutes = 10;
input double PilotRsiBreakevenTriggerPips = 5.0;
input double PilotRsiBreakevenLockPips    = 1.0;
input double PilotRsiTrailingStartPips    = 8.0;
input double PilotRsiTrailingDistancePips = 3.5;
input double PilotRsiTrailingStepPips     = 0.5;
input bool   EnablePilotRsiFailFastProtect = true;
input int    PilotRsiFailFastMinAgeMinutes = 120;
input double PilotRsiFailFastMinLossPips   = 8.0;
input double PilotRsiFailFastMaxLossUSC    = 1.20;
input double PilotRsiFailFastStopBufferPips = 2.5;
input double PilotRsiFailFastStepPips      = 0.5;
input bool   PilotRsiFailFastCloseOnMaxLoss = true;
input bool   EnablePilotRsiTimeStopProtect = true;
input int    PilotRsiMaxHoldMinutes       = 90;
input bool   PilotRsiCloseOnServerDayChange = true;
input bool   PilotRsiBlockSellInUptrend   = true;
input bool   PilotRsiRangeTightBuyOnly    = true;
input bool   PilotRsiSellLiveBlocked      = true;
input bool   EnablePilotBBH1Candidate = true;
input bool   EnablePilotBBH1Live      = false;
input bool   EnableNonRsiLegacyLiveAuthorization = false;
input string NonRsiLegacyLiveAuthorizationTag = "";
input ENUM_TIMEFRAMES PilotBBTimeframe = PERIOD_H1;
input int    PilotBBPeriod            = 20;
input double PilotBBDeviation         = 2.0;
input int    PilotBBRsiPeriod         = 14;
input int    PilotBBRsiOverbought     = 65;
input int    PilotBBRsiOversold       = 35;
input bool   EnablePilotMacdH1Candidate = true;
input bool   EnablePilotMacdH1Live      = false;
input ENUM_TIMEFRAMES PilotMacdTimeframe = PERIOD_H1;
input int    PilotMacdFast            = 12;
input int    PilotMacdSlow            = 26;
input int    PilotMacdSignal          = 9;
input int    PilotMacdLookback        = 24;
input bool   EnablePilotSRM15Candidate = true;
input bool   EnablePilotSRM15Live      = false;
input ENUM_TIMEFRAMES PilotSRTimeframe = PERIOD_M15;
input int    PilotSRLookback          = 24;
input double PilotSRBreakPips         = 2.0;
input ENUM_TIMEFRAMES PilotSignalTimeframe = PERIOD_M15;
input ENUM_TIMEFRAMES PilotTrendTimeframe  = PERIOD_H1;
input int    PilotCrossLookbackBars   = 5;
input int    PilotContinuationLookbackBars = 24;
input bool   PilotBlockRangeEntries   = true;
input int    PilotLossCooldownMinutes = 60;
input bool   EnablePilotBreakevenProtect = true;
input int    PilotBreakevenMinAgeMinutes = 60;
input double PilotBreakevenTriggerPips = 6.0;
input double PilotBreakevenLockPips    = 1.0;
input bool   EnablePilotTrailingStop   = true;
input double PilotTrailingStartPips    = 10.0;
input double PilotTrailingDistancePips = 5.0;
input double PilotTrailingStepPips     = 1.0;
input bool   EnableDemotedPilotRouteExit = true;
input double DemotedPilotRouteProfitExitUSC = 0.0;
input double DemotedPilotRouteMaxLossUSC = 0.50;
input bool   EnableManualSafetyGuard    = false;
input bool   ManualSafetyWatchlistOnly  = false;
input double ManualSafetyInitialSLPips  = 25.0;
input double ManualSafetyBreakevenTriggerPips = 8.0;
input double ManualSafetyBreakevenLockPips    = 1.0;
input bool   EnableManualTrailingStop   = true;
input double ManualSafetyTrailingStartPips    = 10.0;
input double ManualSafetyTrailingDistancePips = 6.0;
input double ManualSafetyTrailingStepPips     = 1.0;
input double ManualSafetyMaxLossUSC     = 20.0;
input bool   ManualSafetyCloseOnMaxLoss = false;
input int    PilotFastMAPeriod        = 9;
input int    PilotSlowMAPeriod        = 21;
input int    PilotTrendMAPeriod       = 200;
input int    PilotATRPeriod           = 14;
input double PilotATRMulitplierSL     = 2.0;
input double PilotRewardRatio         = 1.5;
input double PilotLotSize             = 0.01;
input double PilotMaxSpreadPips       = 2.0;
input int    PilotMaxTotalPositions   = 2;
input int    PilotMaxPositionsPerSymbol = 2;
input bool   PilotRequireStrategyCommentForManagedPosition = true;
input bool   PilotBlockManualPerSymbol  = false;
input bool   PilotRestrictSession       = false;
input int    PilotSessionStartHour      = 0;
input int    PilotSessionEndHour        = 23;
input bool   EnablePilotNewsFilter      = true;
input int    PilotNewsPreBlockMinutes   = 30;
input int    PilotNewsHighImpactPreBlockMinutes = 60;
input int    PilotNewsPostBlockMinutes  = 30;
input int    PilotNewsPostHardBlockMinutes = 5;
input int    PilotNewsBiasMinutes       = 60;
input int    PilotNewsRefreshSeconds    = 15;
input string PilotNewsCurrencies        = "USD,JPY";
input bool   EnableShadowOutcomeLedger  = true;
input int    ShadowOutcomeMaxSourceRows = 800;
input double ShadowOutcomeNeutralPips   = 2.0;
input bool   EnableShadowCandidateRouter = true;
input int    ShadowCandidateMaxSourceRows = 800;
input bool   EnableUsdJpyTokyoBreakoutShadowResearch = true;
input bool   EnableUsdJpyNightReversionShadowResearch = true;
input bool   EnableUsdJpyH4PullbackShadowResearch = true;
input double PilotUsdJpyNoChaseLevel    = 160.0;
input double PilotUsdJpyNoChaseBufferPips = 10.0;
input double PilotMaxFloatingLossUSC    = 30.0;
input double PilotMaxRealizedLossDayUSC = 60.0;
input int    PilotMaxConsecutiveLosses  = 2;
input int    PilotConsecutiveLossPauseMinutes = 180;
input bool   PilotCloseOnKillSwitch     = true;
input long   PilotMagic                 = 520001;
input int    PilotDeviationPoints       = 30;
input bool   EnableUsdJpyKlineExporter  = true;
input int    UsdJpyKlineExportIntervalMinutes = 60;
input int    UsdJpyKlineExportMonths    = 12;
input int    UsdJpyKlineExportMaxBarsPerTimeframe = 700000;
input bool   EnableStrategyJsonEAContractAdapter = true;
input string StrategyJsonEAContractFile = "QuantGod_StrategyJsonEAContract_EA.txt";
input int    StrategyJsonEAContractShadowEvalEverySeconds = 60;
input bool   EnableAutonomousConfigPatchRuntimeAdapter = true;
input string AutonomousConfigPatchRuntimeFile = "QuantGod_AutonomousConfigPatch_EA.txt";

string g_symbols[];
string g_focusSymbol = "";
string g_requestedSymbols[];
string g_resolvedWatchlist = "";
string g_detectedSuffix = "";
string g_strategyKeys[8] =
{
   "MA_Cross",
   "RSI_Reversal",
   "BB_Triple",
   "MACD_Divergence",
   "SR_Breakout",
   "USDJPY_TOKYO_RANGE_BREAKOUT",
   "USDJPY_NIGHT_REVERSION_SAFE",
   "USDJPY_H4_TREND_PULLBACK"
};

CTrade g_trade;

bool   g_autonomousPatchLoaded = false;
bool   g_autonomousPatchRuntimeActive = false;
string g_autonomousPatchStatus = "WAITING_PATCH";
string g_autonomousPatchReasonZh = "等待 Agent 生成 Autonomous Config Patch。";
string g_autonomousPatchAppliedPatchId = "";
string g_autonomousPatchExecutionStage = "";
string g_autonomousPatchRejectedItems = "";
double g_autonomousPatchRsiBuyBand = 0.0;
double g_autonomousPatchRsiCrossbackThreshold = 0.0;
double g_autonomousPatchBreakevenDelayR = 0.0;
double g_autonomousPatchTrailStartR = 0.0;
double g_autonomousPatchMfeGivebackPct = 0.0;
double g_autonomousPatchStageMaxLot = 0.0;
double g_autonomousPatchMaxLot = 0.0;
string g_autonomousConfigPatchStatusJson = "{}";

struct SymbolSnapshot
{
   string   symbol;
   string   role;
   string   status;
   int      tickAgeSeconds;
   double   bid;
   double   ask;
   double   spread;
   int      openPositions;
   double   floatingProfit;
   double   actualFloatingProfit;
   int      closedTrades;
   int      wins;
   double   closedProfit;
   double   actualClosedProfit;
   datetime lastCloseTime;
};

struct StrategyStatusSnapshot
{
   bool     enabled;
   bool     active;
   string   runtimeLabel;
   string   status;
   string   adaptiveState;
   string   adaptiveReason;
   double   riskMultiplier;
   double   score;
   string   reason;
};

struct PilotTelemetrySnapshot
{
   int      dayKey;
   int      evaluationPasses;
   int      signalHits;
   int      waitBarSkips;
   int      noCrossMisses;
   int      spreadBlocks;
   int      sessionBlocks;
   int      newsBlocks;
   int      newsFiltered;
   int      manualBlocks;
   int      portfolioBlocks;
   int      inPositionBlocks;
   int      regimeBlocks;
   int      cooldownBlocks;
   int      startupBlocks;
   int      orderSent;
   int      orderFailed;
   datetime lastEvalTime;
   datetime lastSignalTime;
   datetime lastOrderTime;
   string   lastStatus;
   string   lastReason;
   int      lastDirection;
};

struct ClosedTradeRecord
{
   ulong    ticket;
   ulong    positionId;
   string   type;
   string   symbol;
   double   lots;
   double   actualLots;
   double   virtualLots;
   double   openPrice;
   double   closePrice;
   double   profit;
   double   actualProfit;
   double   swap;
   datetime openTime;
   datetime closeTime;
   string   strategy;
   string   source;
   string   comment;
   string   entryRegime;
   string   exitRegime;
   string   regimeTimeframe;
   int      durationMinutes;
   double   commission;
   double   grossProfit;
};

struct RegimeSnapshot
{
   string   label;
   string   timeframe;
   double   directionalMovePips;
   double   averageRangePips;
   double   recentRangePips;
};

struct TradeJournalRecord
{
   ulong    dealTicket;
   ulong    positionId;
   string   eventType;
   string   side;
   string   symbol;
   double   lots;
   double   price;
   double   grossProfit;
   double   commission;
   double   swap;
   double   netProfit;
   datetime eventTime;
   string   strategy;
   string   source;
   string   comment;
   string   regime;
   string   regimeTimeframe;
};

struct StrategyAggregateRecord
{
   string   symbol;
   string   strategy;
   string   timeframe;
   int      closedTrades;
   int      wins;
   double   grossProfit;
   double   grossLoss;
   double   netProfit;
   datetime lastCloseTime;
   int      openPositions;
   int      strategyPositions;
};

struct RegimeAggregateRecord
{
   string   symbol;
   string   strategy;
   string   timeframe;
   string   entryRegime;
   int      closedTrades;
   int      linkedTrades;
   int      positiveTrades;
   int      negativeTrades;
   int      flatTrades;
   double   grossProfit;
   double   grossLoss;
   double   netProfit;
   double   totalDurationMinutes;
   datetime lastEventTime;
   datetime lastCloseTime;
};

struct NewsFilterState
{
   bool     enabled;
   bool     calendarAvailable;
   bool     blocked;
   bool     biasActive;
   int      usdBiasDirection;
   string   status;
   string   phase;
   string   eventName;
   string   eventCode;
   string   eventCurrency;
   int      eventKind;
   datetime eventTime;
   double   actual;
   double   forecast;
   double   previous;
   int      minutesToEvent;
   int      minutesSinceEvent;
   string   reason;
};

struct ShadowSignalLedgerRecord
{
   string   eventId;
   datetime eventBarTime;
   string   symbol;
   string   strategy;
   string   timeframe;
   string   signalStatus;
   string   signalDirection;
   string   blocker;
   string   executionAction;
   double   referencePrice;
};

struct ShadowCandidateLedgerRecord
{
   string   eventId;
   datetime eventBarTime;
   string   symbol;
   string   candidateRoute;
   string   timeframe;
   string   direction;
   double   score;
   string   regime;
   double   referencePrice;
   string   trigger;
   string   reason;
};

datetime g_lastPilotBarTime[];
datetime g_lastRsiPilotBarTime[];
datetime g_lastBBPilotBarTime[];
datetime g_lastMacdPilotBarTime[];
datetime g_lastSRPilotBarTime[];
datetime g_lastShadowLedgerBarTime[];
datetime g_lastShadowCandidateLedgerBarTime[];
StrategyStatusSnapshot g_maRuntimeStates[];
StrategyStatusSnapshot g_rsiRuntimeStates[];
StrategyStatusSnapshot g_bbRuntimeStates[];
StrategyStatusSnapshot g_macdRuntimeStates[];
StrategyStatusSnapshot g_srRuntimeStates[];
PilotTelemetrySnapshot g_pilotTelemetry[];
bool g_pilotKillSwitch = false;
string g_pilotKillReason = "";
double g_pilotRealizedLossToday = 0.0;
int g_pilotConsecutiveLosses = 0;
datetime g_pilotLatestConsecutiveLossTime = 0;
double g_pilotLatestConsecutiveLossNet = 0.0;
int g_pilotConsecutiveLossPauseRemainingMinutes = 0;
bool g_pilotConsecutiveLossPauseExpired = false;
ulong g_usdTrackedEventIds[];
string g_usdTrackedEventNames[];
string g_usdTrackedEventCodes[];
string g_usdTrackedEventCurrencies[];
int g_usdTrackedEventKinds[];
int g_usdTrackedEventImportance[];
NewsFilterState g_newsState;
datetime g_lastNewsRefresh = 0;
datetime g_lastFullExport = 0;
datetime g_lastPilotTick = 0;
datetime g_lastUsdJpyKlineExport = 0;
datetime g_nextStartupWarmupLog = 0;
datetime g_startupWarmupUntil = 0;
bool g_fullRuntimeInitialized = false;

struct TradeRetryState
{
   int      consecutiveFailures;
   datetime lastFailureAt;
   datetime blockedUntil;
};
TradeRetryState g_tradeRetryState;

datetime g_pilotStartupTime = 0;
datetime g_pilotStartupLocalTime = 0;
datetime g_pilotStartupH1BarTime = 0;

enum ENUM_USD_NEWS_KIND
{
   USD_NEWS_UNKNOWN = 0,
   USD_NEWS_JOBLESS = 1,
   USD_NEWS_PMI     = 2,
   USD_NEWS_CPI     = 3,
   USD_NEWS_GDP     = 4,
   USD_NEWS_RETAIL  = 5,
   USD_NEWS_RATE    = 6,
   USD_NEWS_WAGES   = 7,
   USD_NEWS_TANKAN  = 8,
   USD_NEWS_TRADE   = 9
};

enum ENUM_PILOT_EVAL_CODE
{
   PILOT_EVAL_NONE = 0,
   PILOT_EVAL_NOT_ENOUGH_BARS = 1,
   PILOT_EVAL_TICK_UNAVAILABLE = 2,
   PILOT_EVAL_SPREAD_BLOCK = 3,
   PILOT_EVAL_SESSION_BLOCK = 4,
   PILOT_EVAL_INDICATOR_NOT_READY = 5,
   PILOT_EVAL_TREND_NOT_READY = 6,
   PILOT_EVAL_ATR_UNAVAILABLE = 7,
   PILOT_EVAL_RANGE_BLOCK = 8,
   PILOT_EVAL_SIGNAL_BUY = 9,
   PILOT_EVAL_SIGNAL_SELL = 10,
   PILOT_EVAL_NO_CROSS = 11
};

string TrimString(string value)
{
   int start = 0;
   int end = StringLen(value) - 1;

   while(start <= end)
   {
      ushort c = StringGetCharacter(value, start);
      if(c != ' ' && c != '\t' && c != '\r' && c != '\n')
         break;
      start++;
   }

   while(end >= start)
   {
      ushort c = StringGetCharacter(value, end);
      if(c != ' ' && c != '\t' && c != '\r' && c != '\n')
         break;
      end--;
   }

   if(end < start)
      return "";

   return StringSubstr(value, start, end - start + 1);
}

void PushString(string &values[], string value)
{
   int size = ArraySize(values);
   ArrayResize(values, size + 1);
   values[size] = value;
}

void PushULong(ulong &values[], ulong value)
{
   int size = ArraySize(values);
   ArrayResize(values, size + 1);
   values[size] = value;
}

void PushInt(int &values[], int value)
{
   int size = ArraySize(values);
   ArrayResize(values, size + 1);
   values[size] = value;
}

void PushClosedTrade(ClosedTradeRecord &values[], ClosedTradeRecord &record)
{
   int size = ArraySize(values);
   ArrayResize(values, size + 1);
   values[size] = record;
}

void PushTradeJournal(TradeJournalRecord &values[], TradeJournalRecord &record)
{
   int size = ArraySize(values);
   ArrayResize(values, size + 1);
   values[size] = record;
}

string ToUpperString(string value)
{
   string result = value;
   StringToUpper(result);
   return result;
}

bool ContainsInsensitive(string value, string token)
{
   string haystack = ToUpperString(value);
   string needle = ToUpperString(token);
   return (StringFind(haystack, needle) >= 0);
}

bool EndsWith(string value, string suffix)
{
   int valueLength = StringLen(value);
   int suffixLength = StringLen(suffix);
   if(suffixLength <= 0 || suffixLength > valueLength)
      return false;

   return (StringSubstr(value, valueLength - suffixLength) == suffix);
}

string RemoveTrailingSuffix(string value, string suffix)
{
   if(!EndsWith(value, suffix))
      return value;
   return StringSubstr(value, 0, StringLen(value) - StringLen(suffix));
}

int FindSymbolIndex(string symbol)
{
   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      if(g_symbols[i] == symbol)
         return i;
   }
   return -1;
}

bool SymbolExistsInTerminal(string symbol)
{
   bool isCustom = false;
   return (StringLen(symbol) > 0 && SymbolExist(symbol, isCustom));
}

string DetectAccountSymbolSuffix()
{
   string requested = TrimString(PreferredSymbolSuffix);
   if(StringLen(requested) > 0 && ToUpperString(requested) != "AUTO")
      return requested;

   string chartSymbol = _Symbol;
   if(StringLen(chartSymbol) > 6)
   {
      string chartPrefix = StringSubstr(chartSymbol, 0, 6);
      if(chartPrefix == "EURUSD" || chartPrefix == "USDJPY" || chartPrefix == "GBPUSD")
         return StringSubstr(chartSymbol, 6);
   }

   string accountCurrency = ToUpperString(AccountInfoString(ACCOUNT_CURRENCY));
   if(accountCurrency == "USC")
      return "c";

   string server = ToUpperString(AccountInfoString(ACCOUNT_SERVER));
   if(StringFind(server, "HFMARKETS") >= 0)
   {
      if(SymbolExistsInTerminal("EURUSDc") || SymbolExistsInTerminal("USDJPYc"))
         return "c";
   }

   return "";
}

string ResolveWatchSymbol(string token, string suffix)
{
   string requested = TrimString(token);
   if(StringLen(requested) == 0)
      return "";

   if(SymbolExistsInTerminal(requested))
      return requested;

   string cleanSuffix = TrimString(suffix);
   string normalized = requested;

   if(StringLen(cleanSuffix) > 0)
   {
      normalized = RemoveTrailingSuffix(requested, cleanSuffix);
      string candidate = normalized + cleanSuffix;
      if(SymbolExistsInTerminal(candidate))
         return candidate;
   }

   if(SymbolExistsInTerminal(normalized))
      return normalized;

   if(StringLen(cleanSuffix) == 0 && SymbolExistsInTerminal(normalized + "c"))
      return normalized + "c";

   int symbolsTotal = SymbolsTotal(false);
   string prefixUpper = ToUpperString(normalized);
   string fallback = "";

   for(int i = 0; i < symbolsTotal; i++)
   {
      string symbolName = SymbolName(i, false);
      if(StringLen(symbolName) < StringLen(normalized))
         continue;
      string head = ToUpperString(StringSubstr(symbolName, 0, StringLen(normalized)));
      if(head != prefixUpper)
         continue;

      if(StringLen(cleanSuffix) > 0 && EndsWith(symbolName, cleanSuffix))
         return symbolName;

      if(fallback == "")
         fallback = symbolName;
   }

   return fallback;
}

string JoinResolvedWatchlist()
{
   string value = "";
   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      if(i > 0)
         value += ",";
      value += g_symbols[i];
   }
   return value;
}

string AccountMarginModeToString(long marginMode)
{
   if(marginMode == ACCOUNT_MARGIN_MODE_RETAIL_NETTING)
      return "NETTING";
   if(marginMode == ACCOUNT_MARGIN_MODE_EXCHANGE)
      return "EXCHANGE";
   if(marginMode == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      return "HEDGING";
   return "UNKNOWN";
}

bool InitializeWatchlist()
{
   ArrayResize(g_symbols, 0);
   ArrayResize(g_requestedSymbols, 0);
   string remaining = Watchlist;
   g_detectedSuffix = DetectAccountSymbolSuffix();

   while(StringLen(remaining) > 0)
   {
      int commaPos = StringFind(remaining, ",");
      string token = (commaPos >= 0) ? StringSubstr(remaining, 0, commaPos) : remaining;
      token = TrimString(token);
      if(StringLen(token) > 0)
      {
         PushString(g_requestedSymbols, token);
         string resolved = ResolveWatchSymbol(token, g_detectedSuffix);
         if(StringLen(resolved) > 0 && FindSymbolIndex(resolved) < 0)
            PushString(g_symbols, resolved);
      }
      if(commaPos < 0)
         break;
      remaining = StringSubstr(remaining, commaPos + 1);
   }

   if(ArraySize(g_symbols) == 0)
   {
      string fallback = _Symbol;
      if(StringLen(fallback) == 0)
         fallback = "EURUSD";
      PushString(g_symbols, fallback);
   }

   g_focusSymbol = g_symbols[0];
   g_resolvedWatchlist = JoinResolvedWatchlist();

   for(int i = 0; i < ArraySize(g_symbols); i++)
      SymbolSelect(g_symbols[i], true);

   ArrayResize(g_lastPilotBarTime, ArraySize(g_symbols));
   ArrayResize(g_lastRsiPilotBarTime, ArraySize(g_symbols));
   ArrayResize(g_lastBBPilotBarTime, ArraySize(g_symbols));
   ArrayResize(g_lastMacdPilotBarTime, ArraySize(g_symbols));
   ArrayResize(g_lastSRPilotBarTime, ArraySize(g_symbols));
   ArrayResize(g_lastShadowLedgerBarTime, ArraySize(g_symbols));
   ArrayResize(g_lastShadowCandidateLedgerBarTime, ArraySize(g_symbols));
   ArrayResize(g_maRuntimeStates, ArraySize(g_symbols));
   ArrayResize(g_rsiRuntimeStates, ArraySize(g_symbols));
   ArrayResize(g_bbRuntimeStates, ArraySize(g_symbols));
   ArrayResize(g_macdRuntimeStates, ArraySize(g_symbols));
   ArrayResize(g_srRuntimeStates, ArraySize(g_symbols));
   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      g_lastPilotBarTime[i] = 0;
      g_lastRsiPilotBarTime[i] = 0;
      g_lastBBPilotBarTime[i] = 0;
      g_lastMacdPilotBarTime[i] = 0;
      g_lastSRPilotBarTime[i] = 0;
      g_lastShadowLedgerBarTime[i] = 0;
      g_lastShadowCandidateLedgerBarTime[i] = 0;
      g_maRuntimeStates[i].enabled = false;
      g_maRuntimeStates[i].active = false;
      g_maRuntimeStates[i].runtimeLabel = "PORT";
      g_maRuntimeStates[i].status = "NO_DATA";
      g_maRuntimeStates[i].adaptiveState = "WARMUP";
      g_maRuntimeStates[i].adaptiveReason = "MT5 pilot runtime has not evaluated yet";
      g_maRuntimeStates[i].riskMultiplier = 0.0;
      g_maRuntimeStates[i].score = 0.0;
      g_maRuntimeStates[i].reason = "MT5 pilot runtime has not evaluated yet";
      g_rsiRuntimeStates[i] = g_maRuntimeStates[i];
      g_bbRuntimeStates[i] = g_maRuntimeStates[i];
      g_macdRuntimeStates[i] = g_maRuntimeStates[i];
      g_srRuntimeStates[i] = g_maRuntimeStates[i];
   }

   return true;
}

datetime CurrentServerTime()
{
   datetime value = TimeTradeServer();
   if(value <= 0)
      value = TimeCurrent();
   if(value <= 0)
      value = TimeLocal();
   return value;
}

datetime CurrentHourStart(datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value, parts);
   parts.min = 0;
   parts.sec = 0;
   return StructToTime(parts);
}

void ArmPilotStartupEntryGuard()
{
   g_pilotStartupTime = CurrentServerTime();
   g_pilotStartupLocalTime = TimeLocal();
   g_pilotStartupH1BarTime = 0;
   string symbol = g_focusSymbol;
   if(StringLen(symbol) <= 0 && ArraySize(g_symbols) > 0)
      symbol = g_symbols[0];
   if(StringLen(symbol) > 0)
      g_pilotStartupH1BarTime = iTime(symbol, PERIOD_H1, 0);
   if(g_pilotStartupH1BarTime <= 0)
      g_pilotStartupH1BarTime = CurrentHourStart(g_pilotStartupTime);
}

int PilotStartupEntryGuardRemainingMinutes()
{
   if(!EnablePilotStartupEntryGuard || PilotStartupEntryMinWaitMinutes <= 0 || g_pilotStartupTime <= 0)
      return 0;
   datetime now = TimeLocal();
   datetime start = g_pilotStartupLocalTime > 0 ? g_pilotStartupLocalTime : g_pilotStartupTime;
   int elapsedSeconds = (int)MathMax(0, (long)(now - start));
   int requiredSeconds = MathMax(0, PilotStartupEntryMinWaitMinutes) * 60;
   if(elapsedSeconds >= requiredSeconds)
      return 0;
   return (int)MathCeil((double)(requiredSeconds - elapsedSeconds) / 60.0);
}

bool PilotStartupEntryGuardWaitingForNextH1(string symbol)
{
   if(!EnablePilotStartupEntryGuard || !PilotStartupEntryWaitNextH1Bar)
      return false;
   if(g_pilotStartupH1BarTime <= 0)
      return true;
   datetime currentH1 = 0;
   if(StringLen(symbol) > 0)
      currentH1 = iTime(symbol, PERIOD_H1, 0);
   if(currentH1 <= 0)
      currentH1 = CurrentHourStart(CurrentServerTime());
   return (currentH1 <= g_pilotStartupH1BarTime);
}

bool PilotStartupEntryGuardBlocks(string symbol, string &reason)
{
   reason = "";
   if(!EnablePilotStartupEntryGuard || !IsPilotLiveMode())
      return false;

   int waitMinutes = PilotStartupEntryGuardRemainingMinutes();
   bool waitH1 = PilotStartupEntryGuardWaitingForNextH1(symbol);
   if(waitMinutes <= 0 && !waitH1)
      return false;

   reason = "Pilot startup entry guard active";
   if(waitH1)
      reason += ": waiting for next H1 bar after EA reload";
   if(waitMinutes > 0)
   {
      if(waitH1)
         reason += "; ";
      else
         reason += ": ";
      reason += "minimum wait " + IntegerToString(waitMinutes) + "m remaining";
   }
   return true;
}

void ResetNewsFilterState()
{
   g_newsState.enabled = EnablePilotNewsFilter;
   g_newsState.calendarAvailable = false;
   g_newsState.blocked = false;
   g_newsState.biasActive = false;
   g_newsState.usdBiasDirection = 0;
   g_newsState.status = EnablePilotNewsFilter ? "IDLE" : "DISABLED";
   g_newsState.phase = "none";
   g_newsState.eventName = "";
   g_newsState.eventCode = "";
   g_newsState.eventCurrency = "";
   g_newsState.eventKind = USD_NEWS_UNKNOWN;
   g_newsState.eventTime = 0;
   g_newsState.actual = 0.0;
   g_newsState.forecast = 0.0;
   g_newsState.previous = 0.0;
   g_newsState.minutesToEvent = 0;
   g_newsState.minutesSinceEvent = 0;
   g_newsState.reason = EnablePilotNewsFilter
      ? "USDJPY high-impact news filter is armed"
      : "USDJPY high-impact news filter is disabled";
}

int DetermineUsdNewsKind(string sourceText)
{
   string upper = ToUpperString(sourceText);
   bool looksLikeInitialClaims =
      ((StringFind(upper, "JOBLESS") >= 0 || StringFind(upper, "UNEMPLOYMENT CLAIM") >= 0) &&
       StringFind(upper, "CONTINUING") < 0);
   if(looksLikeInitialClaims)
      return USD_NEWS_JOBLESS;

   if(StringFind(upper, "PMI") >= 0 || StringFind(upper, "PURCHASING MANAGERS") >= 0)
      return USD_NEWS_PMI;

   if(StringFind(upper, "CPI") >= 0 || StringFind(upper, "INFLATION") >= 0 ||
      StringFind(upper, "PCE") >= 0 || StringFind(upper, "PRICE INDEX") >= 0)
      return USD_NEWS_CPI;

   if(StringFind(upper, "GDP") >= 0 || StringFind(upper, "GROSS DOMESTIC") >= 0)
      return USD_NEWS_GDP;

   if(StringFind(upper, "RETAIL") >= 0 || StringFind(upper, "SALES") >= 0 ||
      StringFind(upper, "HOUSEHOLD SPENDING") >= 0)
      return USD_NEWS_RETAIL;

   if(StringFind(upper, "INTEREST RATE") >= 0 || StringFind(upper, "POLICY RATE") >= 0 ||
      StringFind(upper, "RATE DECISION") >= 0 || StringFind(upper, "BOJ") >= 0 ||
      StringFind(upper, "BANK OF JAPAN") >= 0 || StringFind(upper, "FOMC") >= 0)
      return USD_NEWS_RATE;

   if(StringFind(upper, "WAGE") >= 0 || StringFind(upper, "EARNINGS") >= 0 ||
      StringFind(upper, "LABOR CASH") >= 0)
      return USD_NEWS_WAGES;

   if(StringFind(upper, "TANKAN") >= 0)
      return USD_NEWS_TANKAN;

   if(StringFind(upper, "TRADE BALANCE") >= 0 || StringFind(upper, "CURRENT ACCOUNT") >= 0)
      return USD_NEWS_TRADE;

   return USD_NEWS_UNKNOWN;
}

string UsdNewsKindLabel(int kind)
{
   if(kind == USD_NEWS_JOBLESS)
      return "jobless claims";
   if(kind == USD_NEWS_PMI)
      return "PMI";
   if(kind == USD_NEWS_CPI)
      return "inflation/CPI";
   if(kind == USD_NEWS_GDP)
      return "GDP";
   if(kind == USD_NEWS_RETAIL)
      return "retail/sales";
   if(kind == USD_NEWS_RATE)
      return "central bank/rate decision";
   if(kind == USD_NEWS_WAGES)
      return "wages/earnings";
   if(kind == USD_NEWS_TANKAN)
      return "Tankan";
   if(kind == USD_NEWS_TRADE)
      return "trade/current account";
   return "tracked calendar event";
}

bool CalendarFieldToDouble(long rawValue, double &value)
{
   value = 0.0;
   if(rawValue == LONG_MIN)
      return false;
   value = (double)rawValue / 1000000.0;
   return true;
}

void LoadTrackedUsdCalendarEvents()
{
   ArrayResize(g_usdTrackedEventIds, 0);
   ArrayResize(g_usdTrackedEventNames, 0);
   ArrayResize(g_usdTrackedEventCodes, 0);
   ArrayResize(g_usdTrackedEventCurrencies, 0);
   ArrayResize(g_usdTrackedEventKinds, 0);
   ArrayResize(g_usdTrackedEventImportance, 0);

   if(!EnablePilotNewsFilter)
      return;

   string currencies[];
   int currencyCount = StringSplit(PilotNewsCurrencies, ',', currencies);
   if(currencyCount <= 0)
   {
      ArrayResize(currencies, 2);
      currencies[0] = "USD";
      currencies[1] = "JPY";
      currencyCount = 2;
   }

   for(int c = 0; c < currencyCount; c++)
   {
      string currency = ToUpperString(TrimString(currencies[c]));
      if(currency != "USD" && currency != "JPY")
         continue;

      MqlCalendarEvent events[];
      ResetLastError();
      int count = CalendarEventByCurrency(currency, events);
      if(count <= 0)
      {
         Print("QuantGod MT5 news filter failed to load ", currency, " calendar events. err=", GetLastError());
         continue;
      }

      for(int i = 0; i < count; i++)
      {
         if(events[i].type != CALENDAR_TYPE_INDICATOR)
            continue;
         string descriptor = events[i].event_code + " " + events[i].name;
         int kind = DetermineUsdNewsKind(descriptor);
         if(events[i].importance < CALENDAR_IMPORTANCE_HIGH && kind == USD_NEWS_UNKNOWN)
            continue;

         PushULong(g_usdTrackedEventIds, events[i].id);
         PushString(g_usdTrackedEventNames, events[i].name);
         PushString(g_usdTrackedEventCodes, events[i].event_code);
         PushString(g_usdTrackedEventCurrencies, currency);
         PushInt(g_usdTrackedEventKinds, kind);
         PushInt(g_usdTrackedEventImportance, (int)events[i].importance);
         if(ArraySize(g_usdTrackedEventIds) >= 80)
            break;
      }
      if(ArraySize(g_usdTrackedEventIds) >= 80)
         break;
   }

   if(ArraySize(g_usdTrackedEventIds) > 0)
   {
      Print("QuantGod MT5 news filter armed with ", ArraySize(g_usdTrackedEventIds),
            " USDJPY calendar events from ", PilotNewsCurrencies);
   }
   else
   {
      Print("QuantGod MT5 news filter found no matching USDJPY events in terminal calendar");
   }
}

int UsdBiasFromEventKind(int kind, double actual, double forecast)
{
   double diff = actual - forecast;
   if(MathAbs(diff) < 0.000001)
      return 0;

   if(kind == USD_NEWS_JOBLESS)
      return (diff < 0.0) ? 1 : -1;

   if(kind == USD_NEWS_PMI ||
      kind == USD_NEWS_CPI ||
      kind == USD_NEWS_GDP ||
      kind == USD_NEWS_RETAIL ||
      kind == USD_NEWS_RATE ||
      kind == USD_NEWS_WAGES ||
      kind == USD_NEWS_TANKAN ||
      kind == USD_NEWS_TRADE)
      return (diff > 0.0) ? 1 : -1;

   return 0;
}

int PilotDirectionBiasForEventCurrency(string symbol, string currency, int currencyBiasDirection)
{
   if(currencyBiasDirection == 0)
      return 0;

   string upper = ToUpperString(symbol);
   string cur = ToUpperString(currency);
   if(StringFind(upper, "USDJPY") >= 0)
   {
      if(cur == "USD")
         return currencyBiasDirection;
      if(cur == "JPY")
         return -currencyBiasDirection;
   }
   if(StringFind(upper, "EURUSD") >= 0 && cur == "USD")
      return -currencyBiasDirection;
   return 0;
}

string UsdBiasLabel(int direction)
{
   if(direction > 0)
      return "USDJPY_BUY_BIAS";
   if(direction < 0)
      return "USDJPY_SELL_BIAS";
   return "NEUTRAL";
}

int PilotDirectionBiasForSymbol(string symbol, int usdBiasDirection)
{
   if(usdBiasDirection == 0)
      return 0;

   string upper = ToUpperString(symbol);
   if(StringFind(upper, "EURUSD") >= 0)
      return -usdBiasDirection;
   if(StringFind(upper, "USDJPY") >= 0)
      return usdBiasDirection;
   return 0;
}

string PilotActionLabelForSymbol(string symbol)
{
   if(g_newsState.blocked)
      return "BLOCKED";

   int direction = PilotDirectionBiasForSymbol(symbol, g_newsState.usdBiasDirection);
   if(direction > 0)
      return "BUY_ONLY";
   if(direction < 0)
      return "SELL_ONLY";
   return "BOTH";
}

void RefreshNewsFilterState(bool force=false)
{
   if(!EnablePilotNewsFilter)
   {
      ResetNewsFilterState();
      return;
   }

   datetime now = CurrentServerTime();
   if(!force && g_lastNewsRefresh > 0 && (now - g_lastNewsRefresh) < MathMax(5, PilotNewsRefreshSeconds))
      return;
   g_lastNewsRefresh = now;

   ResetNewsFilterState();

   if(ArraySize(g_usdTrackedEventIds) == 0)
      LoadTrackedUsdCalendarEvents();

   if(ArraySize(g_usdTrackedEventIds) == 0)
   {
      g_newsState.status = "NO_CALENDAR";
      g_newsState.reason = "USDJPY calendar events unavailable in this terminal";
      return;
   }

   g_newsState.calendarAvailable = true;

   int maxPreBlockMinutes = MathMax(PilotNewsPreBlockMinutes, PilotNewsHighImpactPreBlockMinutes);
   datetime fromTime = now - (MathMax(PilotNewsBiasMinutes, PilotNewsPostBlockMinutes) + 60) * 60;
   datetime toTime = now + MathMax(360, maxPreBlockMinutes + 60) * 60;

   bool hasPreBlock = false;
   datetime preBlockTime = 0;
   string preBlockName = "";
   string preBlockCode = "";
   string preBlockCurrency = "";
   int preBlockKind = USD_NEWS_UNKNOWN;
   int preBlockMinutes = 0;

   bool hasPostBlock = false;
   datetime postBlockTime = 0;
   string postBlockName = "";
   string postBlockCode = "";
   string postBlockCurrency = "";
   int postBlockKind = USD_NEWS_UNKNOWN;
   int postBlockMinutes = 0;

   bool hasUpcoming = false;
   datetime upcomingTime = 0;
   string upcomingName = "";
   string upcomingCode = "";
   string upcomingCurrency = "";
   int upcomingKind = USD_NEWS_UNKNOWN;
   int upcomingMinutes = 0;

   int biasScore = 0;
   int biasSamples = 0;
   datetime biasEventTime = 0;
   string biasEventName = "";
   string biasEventCode = "";
   string biasEventCurrency = "";
   int biasEventKind = USD_NEWS_UNKNOWN;
   double biasActual = 0.0;
   double biasForecast = 0.0;
   double biasPrevious = 0.0;
   int biasMinutesSince = 0;

   for(int i = 0; i < ArraySize(g_usdTrackedEventIds); i++)
   {
      MqlCalendarValue values[];
      ResetLastError();
      int count = CalendarValueHistoryByEvent(g_usdTrackedEventIds[i], values, fromTime, toTime);
      if(count < 0)
         continue;

      for(int j = 0; j < count; j++)
      {
         datetime eventTime = values[j].time;
         if(eventTime <= 0)
            continue;

         string eventName = g_usdTrackedEventNames[i];
         string eventCode = (i < ArraySize(g_usdTrackedEventCodes)) ? g_usdTrackedEventCodes[i] : "";
         string eventCurrency = (i < ArraySize(g_usdTrackedEventCurrencies)) ? g_usdTrackedEventCurrencies[i] : "USD";
         int eventKind = (i < ArraySize(g_usdTrackedEventKinds)) ? g_usdTrackedEventKinds[i] : USD_NEWS_UNKNOWN;
         int eventImportance = (i < ArraySize(g_usdTrackedEventImportance)) ? g_usdTrackedEventImportance[i] : (int)CALENDAR_IMPORTANCE_MODERATE;
         if(eventTime > now)
         {
            int minutesToEvent = (int)MathMax(0, (long)(eventTime - now) / 60);
            int preBlockWindow = PilotNewsPreBlockMinutes;
            if(eventImportance >= (int)CALENDAR_IMPORTANCE_HIGH)
               preBlockWindow = MathMax(preBlockWindow, PilotNewsHighImpactPreBlockMinutes);
            if(!hasUpcoming || eventTime < upcomingTime)
            {
               hasUpcoming = true;
               upcomingTime = eventTime;
               upcomingName = eventName;
               upcomingCode = eventCode;
               upcomingCurrency = eventCurrency;
               upcomingKind = eventKind;
               upcomingMinutes = minutesToEvent;
            }
            if(minutesToEvent <= preBlockWindow && (!hasPreBlock || eventTime < preBlockTime))
            {
               hasPreBlock = true;
               preBlockTime = eventTime;
               preBlockName = eventName;
               preBlockCode = eventCode;
               preBlockCurrency = eventCurrency;
               preBlockKind = eventKind;
               preBlockMinutes = minutesToEvent;
            }
            continue;
         }

         int minutesSinceEvent = (int)MathMax(0, (long)(now - eventTime) / 60);
         double actual = 0.0;
         double forecast = 0.0;
         double previous = 0.0;
         bool hasActual = CalendarFieldToDouble(values[j].actual_value, actual);
         bool hasForecast = CalendarFieldToDouble(values[j].forecast_value, forecast);
         bool hasPrevious = CalendarFieldToDouble(values[j].prev_value, previous);
         if(!hasPrevious)
            CalendarFieldToDouble(values[j].revised_prev_value, previous);

         int currencyBias = (hasActual && hasForecast) ? UsdBiasFromEventKind(eventKind, actual, forecast) : 0;
         int eventBias = PilotDirectionBiasForEventCurrency(g_focusSymbol, eventCurrency, currencyBias);
         bool hasDirectionalBias = (eventBias != 0);

         if(minutesSinceEvent <= PilotNewsPostBlockMinutes)
         {
            int hardPostWindow = MathMin(PilotNewsPostBlockMinutes, MathMax(0, PilotNewsPostHardBlockMinutes));
            bool hardBlock = (minutesSinceEvent <= hardPostWindow || !hasDirectionalBias);
            if(hardBlock && (!hasPostBlock || eventTime > postBlockTime))
            {
               hasPostBlock = true;
               postBlockTime = eventTime;
               postBlockName = eventName;
               postBlockCode = eventCode;
               postBlockCurrency = eventCurrency;
               postBlockKind = eventKind;
               postBlockMinutes = minutesSinceEvent;
            }
         }

         if(!hasActual || !hasForecast || minutesSinceEvent > PilotNewsBiasMinutes)
            continue;

         if(eventBias == 0)
            continue;

         biasScore += eventBias;
         biasSamples++;
         if(eventTime >= biasEventTime)
         {
            biasEventTime = eventTime;
            biasEventName = eventName;
            biasEventCode = eventCode;
            biasEventCurrency = eventCurrency;
            biasEventKind = eventKind;
            biasActual = actual;
            biasForecast = forecast;
            biasPrevious = previous;
            biasMinutesSince = minutesSinceEvent;
         }
      }
   }

   if(hasPreBlock)
   {
      g_newsState.blocked = true;
      g_newsState.status = "PRE_BLOCK";
      g_newsState.phase = "pre";
      g_newsState.eventName = preBlockName;
      g_newsState.eventCode = preBlockCode;
      g_newsState.eventCurrency = preBlockCurrency;
      g_newsState.eventKind = preBlockKind;
      g_newsState.eventTime = preBlockTime;
      g_newsState.minutesToEvent = preBlockMinutes;
      g_newsState.reason = "USDJPY news pre-block: " + CurrentNewsEventLabel() +
         " in " + IntegerToString(preBlockMinutes) + "m";
      return;
   }

   if(hasPostBlock)
   {
      g_newsState.blocked = true;
      g_newsState.status = "POST_BLOCK";
      g_newsState.phase = "post";
      g_newsState.eventName = postBlockName;
      g_newsState.eventCode = postBlockCode;
      g_newsState.eventCurrency = postBlockCurrency;
      g_newsState.eventKind = postBlockKind;
      g_newsState.eventTime = postBlockTime;
      g_newsState.minutesSinceEvent = postBlockMinutes;
      g_newsState.reason = "USDJPY news post-release hard cooldown: " + CurrentNewsEventLabel() +
         " +" + IntegerToString(postBlockMinutes) + "m";
      return;
   }

   if(biasSamples > 0 && biasScore != 0)
   {
      g_newsState.biasActive = true;
      g_newsState.usdBiasDirection = (biasScore > 0) ? 1 : -1;
      g_newsState.status = "BIAS_ACTIVE";
      g_newsState.phase = "bias";
      g_newsState.eventName = biasEventName;
      g_newsState.eventCode = biasEventCode;
      g_newsState.eventCurrency = biasEventCurrency;
      g_newsState.eventKind = biasEventKind;
      g_newsState.eventTime = biasEventTime;
      g_newsState.actual = biasActual;
      g_newsState.forecast = biasForecast;
      g_newsState.previous = biasPrevious;
      g_newsState.minutesSinceEvent = biasMinutesSince;
      g_newsState.reason = "USDJPY news bias " + UsdBiasLabel(g_newsState.usdBiasDirection) +
         " from " + CurrentNewsEventLabel() +
         " | actual=" + DoubleToString(biasActual, 2) +
         " forecast=" + DoubleToString(biasForecast, 2);
      return;
   }

   if(hasUpcoming)
   {
      g_newsState.status = "TRACKING";
      g_newsState.phase = "tracking";
      g_newsState.eventName = upcomingName;
      g_newsState.eventCode = upcomingCode;
      g_newsState.eventCurrency = upcomingCurrency;
      g_newsState.eventKind = upcomingKind;
      g_newsState.eventTime = upcomingTime;
      g_newsState.minutesToEvent = upcomingMinutes;
      g_newsState.reason = "Tracking next USDJPY event: " + CurrentNewsEventLabel() +
         " in " + IntegerToString(upcomingMinutes) + "m";
      return;
   }

   g_newsState.status = "IDLE";
   g_newsState.reason = "No tracked USDJPY event near the current pilot window";
}

bool PilotNewsBlocksSymbol(string symbol, string &reason)
{
   reason = "";
   if(!EnablePilotNewsFilter || !g_newsState.blocked)
      return false;

   int directionBias = PilotDirectionBiasForSymbol(symbol, 1);
   if(directionBias == 0)
      return false;

   reason = SafeNewsReasonText(g_newsState.reason);
   return true;
}

bool IsDisplaySafeAscii(string value)
{
   for(int i = 0; i < StringLen(value); i++)
   {
      ushort ch = StringGetCharacter(value, i);
      if(ch == 9 || ch == 10 || ch == 13)
         continue;
      if(ch < 32 || ch > 126)
         return false;
   }
   return true;
}

string SafeNewsEventName(string value)
{
   if(StringLen(value) <= 0)
      return "";
   if(IsDisplaySafeAscii(value))
      return value;
   return "tracked event";
}

string SafeNewsEventLabel(string eventCode, string eventName, int eventKind)
{
   string safeCode = TrimString(eventCode);
   if(StringLen(safeCode) > 0 && IsDisplaySafeAscii(safeCode))
      return safeCode;

   string safeName = SafeNewsEventName(eventName);
   if(StringLen(safeName) > 0 && safeName != "tracked event")
      return safeName;

   return UsdNewsKindLabel(eventKind);
}

string CurrentNewsEventLabel()
{
   return SafeNewsEventLabel(g_newsState.eventCode, g_newsState.eventName, g_newsState.eventKind);
}

string SafeNewsReasonText(string reason)
{
   if(StringLen(reason) <= 0)
      return reason;

   string safeReason = reason;
   string safeEvent = CurrentNewsEventLabel();
   if(StringLen(g_newsState.eventName) > 0)
      StringReplace(safeReason, g_newsState.eventName, safeEvent);

   if(IsDisplaySafeAscii(safeReason))
      return safeReason;

   string label = (StringLen(safeEvent) > 0) ? safeEvent : "USDJPY calendar event";
   if(g_newsState.status == "PRE_BLOCK")
      return "USDJPY news pre-block: " + label + " in " + IntegerToString(g_newsState.minutesToEvent) + "m";
   if(g_newsState.status == "POST_BLOCK")
      return "USDJPY news post-release hard cooldown: " + label + " +" + IntegerToString(g_newsState.minutesSinceEvent) + "m";
   if(g_newsState.status == "BIAS_ACTIVE")
      return "USDJPY news bias " + UsdBiasLabel(g_newsState.usdBiasDirection) +
         " from " + label +
         " | actual=" + DoubleToString(g_newsState.actual, 2) +
         " forecast=" + DoubleToString(g_newsState.forecast, 2);
   if(g_newsState.status == "TRACKING")
      return "Tracking next USDJPY event: " + label + " in " + IntegerToString(g_newsState.minutesToEvent) + "m";
   return "USDJPY news filter: " + label;
}

bool PilotDirectionAllowedByNews(string symbol, int direction, MqlTick &tick, string &reason)
{
   reason = "";
   if(!EnablePilotNewsFilter)
      return true;

   if(g_newsState.blocked)
   {
      reason = SafeNewsReasonText(g_newsState.reason);
      return false;
   }

   int preferredDirection = PilotDirectionBiasForSymbol(symbol, g_newsState.usdBiasDirection);
   if(g_newsState.biasActive && preferredDirection != 0 && direction != preferredDirection)
   {
      reason = "News bias allows only " + PilotActionLabelForSymbol(symbol) +
         " after " + CurrentNewsEventLabel();
      return false;
   }

   string upper = ToUpperString(symbol);
   if(g_newsState.biasActive &&
      g_newsState.usdBiasDirection > 0 &&
      direction > 0 &&
      StringFind(upper, "USDJPY") >= 0)
   {
      double noChasePrice = PilotUsdJpyNoChaseLevel - (PilotUsdJpyNoChaseBufferPips * PipSize(symbol));
      if(tick.ask >= noChasePrice)
      {
         reason = "USDJPY anti-chase guard near 160 blocks breakout BUY after positive USDJPY news bias";
         return false;
      }
   }

   return true;
}

string BuildNewsJson()
{
   bool calendarAvailable = g_newsState.calendarAvailable || ArraySize(g_usdTrackedEventIds) > 0;
   string newsReason = g_newsState.reason;
   if(EnablePilotNewsFilter &&
      calendarAvailable &&
      g_newsState.status == "IDLE" &&
      g_newsState.reason == "USDJPY high-impact news filter is armed")
   {
      newsReason = "No tracked USDJPY event near the current pilot window";
   }
   string safeEventName = SafeNewsEventName(g_newsState.eventName);
   string safeEventLabel = CurrentNewsEventLabel();
   newsReason = SafeNewsReasonText(newsReason);

   string json = "{";
   json += "\"enabled\": " + JsonBool(EnablePilotNewsFilter) + ", ";
   json += "\"calendarAvailable\": " + JsonBool(calendarAvailable) + ", ";
   json += "\"trackedEvents\": " + IntegerToString(ArraySize(g_usdTrackedEventIds)) + ", ";
   json += "\"status\": \"" + JsonEscape(g_newsState.status) + "\", ";
   json += "\"phase\": \"" + JsonEscape(g_newsState.phase) + "\", ";
   json += "\"blocked\": " + JsonBool(g_newsState.blocked) + ", ";
   json += "\"biasActive\": " + JsonBool(g_newsState.biasActive) + ", ";
   json += "\"usdBias\": \"" + JsonEscape(UsdBiasLabel(g_newsState.usdBiasDirection)) + "\", ";
   json += "\"eventName\": \"" + JsonEscape(safeEventName) + "\", ";
   json += "\"eventCode\": \"" + JsonEscape(g_newsState.eventCode) + "\", ";
   json += "\"eventCurrency\": \"" + JsonEscape(g_newsState.eventCurrency) + "\", ";
   json += "\"eventKind\": \"" + JsonEscape(UsdNewsKindLabel(g_newsState.eventKind)) + "\", ";
   json += "\"eventLabel\": \"" + JsonEscape(safeEventLabel) + "\", ";
   json += "\"eventTimeServer\": \"" + JsonEscape(FormatDateTime(g_newsState.eventTime, true)) + "\", ";
   json += "\"minutesToEvent\": " + IntegerToString(g_newsState.minutesToEvent) + ", ";
   json += "\"minutesSinceEvent\": " + IntegerToString(g_newsState.minutesSinceEvent) + ", ";
   json += "\"actual\": " + FormatNumber(g_newsState.actual, 2) + ", ";
   json += "\"forecast\": " + FormatNumber(g_newsState.forecast, 2) + ", ";
   json += "\"previous\": " + FormatNumber(g_newsState.previous, 2) + ", ";
   json += "\"focusAction\": \"" + JsonEscape(PilotActionLabelForSymbol(g_focusSymbol)) + "\", ";
   json += "\"reason\": \"" + JsonEscape(newsReason) + "\"";
   json += "}";
   return json;
}

bool IsPilotLiveMode()
{
   return (EnablePilotAutoTrading && !ReadOnlyMode);
}

string SymbolTradeModeLabel(long mode)
{
   if(mode == SYMBOL_TRADE_MODE_DISABLED)
      return "DISABLED";
   if(mode == SYMBOL_TRADE_MODE_LONGONLY)
      return "LONG_ONLY";
   if(mode == SYMBOL_TRADE_MODE_SHORTONLY)
      return "SHORT_ONLY";
   if(mode == SYMBOL_TRADE_MODE_CLOSEONLY)
      return "CLOSE_ONLY";
   if(mode == SYMBOL_TRADE_MODE_FULL)
      return "FULL";
   return "UNKNOWN";
}

bool SymbolEntryTradeAllowed(string symbol)
{
   long tradeMode = SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   return (tradeMode == SYMBOL_TRADE_MODE_FULL);
}

string LiveTradePermissionBlocker(string symbol)
{
   if(ReadOnlyMode)
      return "READ_ONLY_MODE";
   if(!(bool)TerminalInfoInteger(TERMINAL_CONNECTED))
      return "TERMINAL_DISCONNECTED";
   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
      return "TERMINAL_AUTOTRADING_DISABLED";
   if(!(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
      return "EA_LIVE_TRADING_DISABLED";
   if(!(bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
      return "ACCOUNT_TRADE_DISABLED_OR_INVESTOR_MODE";
   if(!(bool)AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
      return "ACCOUNT_EXPERT_TRADE_DISABLED";
   if(!SymbolEntryTradeAllowed(symbol))
      return "SYMBOL_TRADE_MODE_" + SymbolTradeModeLabel(SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE));
   return "";
}

bool IsUsdJpySymbol(string symbol)
{
   return (StringFind(ToUpperString(symbol), "USDJPY") >= 0);
}

bool IsRangeTightRegimeLabel(string label)
{
   return (ToUpperString(label) == "RANGE_TIGHT");
}

int ServerDayKeyFromTime(datetime value)
{
   if(value <= 0)
      return 0;
   MqlDateTime dt;
   TimeToStruct(value, dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
}

datetime ServerTimeToJst(datetime value)
{
   if(value <= 0)
      value = CurrentServerTime();
   datetime serverNow = CurrentServerTime();
   datetime gmtNow = TimeGMT();
   int serverOffsetSeconds = 0;
   if(serverNow > 0 && gmtNow > 0)
      serverOffsetSeconds = (int)(serverNow - gmtNow);
   return value - serverOffsetSeconds + 9 * 3600;
}

int JstDayKeyFromServerTime(datetime value)
{
   datetime jst = ServerTimeToJst(value);
   MqlDateTime dt;
   TimeToStruct(jst, dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
}

int JstMinuteOfDayFromServerTime(datetime value)
{
   datetime jst = ServerTimeToJst(value);
   MqlDateTime dt;
   TimeToStruct(jst, dt);
   return dt.hour * 60 + dt.min;
}

bool IsUsdJpyShadowResearchRoute(string strategyKey)
{
   return (strategyKey == "USDJPY_TOKYO_RANGE_BREAKOUT" ||
           strategyKey == "USDJPY_NIGHT_REVERSION_SAFE" ||
           strategyKey == "USDJPY_H4_TREND_PULLBACK");
}

bool IsUsdJpyShadowResearchRouteEnabled(string strategyKey)
{
   if(strategyKey == "USDJPY_TOKYO_RANGE_BREAKOUT")
      return EnableUsdJpyTokyoBreakoutShadowResearch;
   if(strategyKey == "USDJPY_NIGHT_REVERSION_SAFE")
      return EnableUsdJpyNightReversionShadowResearch;
   if(strategyKey == "USDJPY_H4_TREND_PULLBACK")
      return EnableUsdJpyH4PullbackShadowResearch;
   return false;
}

bool IsLegacyPilotRouteCandidateEnabled(string strategyKey)
{
   if(strategyKey == "RSI_Reversal")
      return (EnablePilotRsiH1Candidate || EnablePilotRsiH1Live);
   if(strategyKey == "BB_Triple")
      return (EnablePilotBBH1Candidate || EnablePilotBBH1Live);
   if(strategyKey == "MACD_Divergence")
      return (EnablePilotMacdH1Candidate || EnablePilotMacdH1Live);
   if(strategyKey == "SR_Breakout")
      return (EnablePilotSRM15Candidate || EnablePilotSRM15Live);
   return false;
}

bool IsNonRsiLegacyPilotRoute(string strategyKey)
{
   return (strategyKey == "BB_Triple" ||
           strategyKey == "MACD_Divergence" ||
           strategyKey == "SR_Breakout");
}

bool IsNonRsiLegacyAuthorizationTesterMode()
{
   return (MQLInfoInteger(MQL_TESTER) != 0);
}

string NonRsiLegacyLiveAuthorizationExpectedTag()
{
   return IsNonRsiLegacyAuthorizationTesterMode()
      ? "ALLOW_NON_RSI_LEGACY_TESTER"
      : "ALLOW_NON_RSI_LEGACY_LIVE";
}

bool NonRsiLegacyLiveAuthorizationActive()
{
   string normalizedTag = ToUpperString(NonRsiLegacyLiveAuthorizationTag);
   return (EnableNonRsiLegacyLiveAuthorization &&
           normalizedTag == NonRsiLegacyLiveAuthorizationExpectedTag());
}

string NonRsiLegacyLiveAuthorizationState()
{
   if(!EnableNonRsiLegacyLiveAuthorization)
      return "DISABLED";
   if(NonRsiLegacyLiveAuthorizationActive())
      return IsNonRsiLegacyAuthorizationTesterMode() ? "TESTER_AUTHORIZED" : "LIVE_AUTHORIZED";
   return IsNonRsiLegacyAuthorizationTesterMode() ? "TESTER_TAG_MISMATCH" : "LIVE_TAG_MISMATCH";
}

bool IsLegacyPilotRouteLiveEnabled(string strategyKey)
{
   if(!IsPilotLiveMode())
      return false;
   // RSI is still gated by IsPilotLiveMode() above and its own live switch.
   // The extra non-RSI authorization lock applies only to BB/MACD/SR.
   if(strategyKey == "RSI_Reversal")
      return EnablePilotRsiH1Live;
   if(strategyKey == "BB_Triple")
      return (EnablePilotBBH1Live && NonRsiLegacyLiveAuthorizationActive());
   if(strategyKey == "MACD_Divergence")
      return (EnablePilotMacdH1Live && NonRsiLegacyLiveAuthorizationActive());
   if(strategyKey == "SR_Breakout")
      return (EnablePilotSRM15Live && NonRsiLegacyLiveAuthorizationActive());
   return false;
}

bool IsPilotStrategyComment(string comment)
{
   string upper = ToUpperString(comment);
   return (StringFind(upper, "QG_MA_CROSS_MT5") >= 0 ||
           StringFind(upper, "QG_MA_CROSS") >= 0 ||
           StringFind(upper, "QG_RSI_REV") >= 0 ||
           StringFind(upper, "QG_BB_TRIPLE") >= 0 ||
           StringFind(upper, "QG_MACD_DIV") >= 0 ||
           StringFind(upper, "QG_SR_BREAK") >= 0);
}

bool IsPilotRsiPositionComment(string comment)
{
   return (StringFind(ToUpperString(comment), "QG_RSI_REV") >= 0);
}

string PilotTradeComment(string strategyKey, int direction)
{
   if(strategyKey == "RSI_Reversal")
      return (direction > 0) ? "QG_RSI_Rev_MT5_BUY" : "QG_RSI_Rev_MT5_SELL";
   if(strategyKey == "BB_Triple")
      return (direction > 0) ? "QG_BB_Triple_MT5_BUY" : "QG_BB_Triple_MT5_SELL";
   if(strategyKey == "MACD_Divergence")
      return (direction > 0) ? "QG_MACD_Div_MT5_BUY" : "QG_MACD_Div_MT5_SELL";
   if(strategyKey == "SR_Breakout")
      return (direction > 0) ? "QG_SR_Break_MT5_BUY" : "QG_SR_Break_MT5_SELL";
   return (direction > 0) ? "QG_MA_Cross_MT5_BUY" : "QG_MA_Cross_MT5_SELL";
}

double NormalizeVolumeForSymbol(string symbol, double requested)
{
   double minVolume = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxVolume = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(minVolume <= 0.0)
      minVolume = 0.01;
   if(maxVolume <= 0.0)
      maxVolume = requested;
   if(step <= 0.0)
      step = minVolume;

   double volume = requested;
   volume = MathMax(minVolume, MathMin(maxVolume, volume));
   volume = MathFloor(volume / step + 1e-8) * step;
   if(volume < minVolume)
      volume = minVolume;
   return volume;
}

void ResetPilotRuntimeStates()
{
   g_pilotKillSwitch = false;
   g_pilotKillReason = "";
   g_pilotRealizedLossToday = 0.0;
   g_pilotConsecutiveLosses = 0;
   g_pilotLatestConsecutiveLossTime = 0;
   g_pilotLatestConsecutiveLossNet = 0.0;
   g_pilotConsecutiveLossPauseRemainingMinutes = 0;
   g_pilotConsecutiveLossPauseExpired = false;

   for(int i = 0; i < ArraySize(g_maRuntimeStates); i++)
   {
      g_maRuntimeStates[i].enabled = IsPilotLiveMode() && EnablePilotMA;
      g_maRuntimeStates[i].active = false;
      g_maRuntimeStates[i].runtimeLabel = g_maRuntimeStates[i].enabled ? "OFF" : "PORT";
      g_maRuntimeStates[i].status = g_maRuntimeStates[i].enabled ? "WAIT_SIGNAL" : "NO_DATA";
      g_maRuntimeStates[i].adaptiveState = g_maRuntimeStates[i].enabled ? "CAUTION" : "WARMUP";
      g_maRuntimeStates[i].adaptiveReason = g_maRuntimeStates[i].enabled
         ? "MT5 0.01 live pilot armed: M15 signal, H1 trend filter, 5-bar cross plus 24-bar pullback continuation, range guard, and post-loss cooldown"
         : "MT5 phase 1 skeleton: execution engine not ported yet";
      g_maRuntimeStates[i].riskMultiplier = g_maRuntimeStates[i].enabled ? 1.0 : 0.0;
      g_maRuntimeStates[i].score = 0.0;
      g_maRuntimeStates[i].reason = g_maRuntimeStates[i].enabled
         ? "Waiting for first pilot evaluation"
         : "MT5 phase 1 skeleton: execution engine not ported yet";

      bool rsiEnabled = IsLegacyPilotRouteCandidateEnabled("RSI_Reversal") && IsUsdJpySymbol(g_symbols[i]);
      g_rsiRuntimeStates[i].enabled = rsiEnabled;
      g_rsiRuntimeStates[i].active = false;
      g_rsiRuntimeStates[i].runtimeLabel = rsiEnabled ? (IsLegacyPilotRouteLiveEnabled("RSI_Reversal") ? "ON" : "CAND") : "PORT";
      g_rsiRuntimeStates[i].status = rsiEnabled ? "WAIT_SIGNAL" : "NO_DATA";
      g_rsiRuntimeStates[i].adaptiveState = IsLegacyPilotRouteLiveEnabled("RSI_Reversal") ? "CAUTION" : "CANDIDATE";
      g_rsiRuntimeStates[i].adaptiveReason = rsiEnabled
         ? "USDJPY RSI_Reversal H1 route ported from MT4; live entry gated by EnablePilotRsiH1Live and shared pilot risk controls"
         : "MT5 RSI_Reversal route is scoped to USDJPY candidate/backtest validation";
      g_rsiRuntimeStates[i].riskMultiplier = IsLegacyPilotRouteLiveEnabled("RSI_Reversal") ? 1.0 : 0.0;
      g_rsiRuntimeStates[i].score = 0.0;
      g_rsiRuntimeStates[i].reason = rsiEnabled ? "Waiting for first H1 RSI evaluation" : "Not in USDJPY RSI candidate scope";

      bool bbEnabled = IsLegacyPilotRouteCandidateEnabled("BB_Triple");
      g_bbRuntimeStates[i].enabled = bbEnabled;
      g_bbRuntimeStates[i].active = false;
      g_bbRuntimeStates[i].runtimeLabel = bbEnabled ? (IsLegacyPilotRouteLiveEnabled("BB_Triple") ? "ON" : "CAND") : "PORT";
      g_bbRuntimeStates[i].status = bbEnabled ? "WAIT_SIGNAL" : "NO_DATA";
      g_bbRuntimeStates[i].adaptiveState = IsLegacyPilotRouteLiveEnabled("BB_Triple") ? "CAUTION" : "CANDIDATE";
      g_bbRuntimeStates[i].adaptiveReason = bbEnabled
         ? "BB_Triple H1 route ported from MT4; live entry requires EnablePilotBBH1Live plus the non-RSI legacy authorization tag"
         : "MT5 BB_Triple route is disabled";
      g_bbRuntimeStates[i].riskMultiplier = IsLegacyPilotRouteLiveEnabled("BB_Triple") ? 1.0 : 0.0;
      g_bbRuntimeStates[i].score = 0.0;
      g_bbRuntimeStates[i].reason = bbEnabled ? "Waiting for first H1 BB evaluation" : "BB_Triple route disabled";

      bool macdEnabled = IsLegacyPilotRouteCandidateEnabled("MACD_Divergence");
      g_macdRuntimeStates[i].enabled = macdEnabled;
      g_macdRuntimeStates[i].active = false;
      g_macdRuntimeStates[i].runtimeLabel = macdEnabled ? (IsLegacyPilotRouteLiveEnabled("MACD_Divergence") ? "ON" : "CAND") : "PORT";
      g_macdRuntimeStates[i].status = macdEnabled ? "WAIT_SIGNAL" : "NO_DATA";
      g_macdRuntimeStates[i].adaptiveState = IsLegacyPilotRouteLiveEnabled("MACD_Divergence") ? "CAUTION" : "CANDIDATE";
      g_macdRuntimeStates[i].adaptiveReason = macdEnabled
         ? "MACD_Divergence H1 route ported from MT4; live entry requires EnablePilotMacdH1Live plus the non-RSI legacy authorization tag"
         : "MT5 MACD_Divergence route is disabled";
      g_macdRuntimeStates[i].riskMultiplier = IsLegacyPilotRouteLiveEnabled("MACD_Divergence") ? 1.0 : 0.0;
      g_macdRuntimeStates[i].score = 0.0;
      g_macdRuntimeStates[i].reason = macdEnabled ? "Waiting for first H1 MACD divergence evaluation" : "MACD_Divergence route disabled";

      bool srEnabled = IsLegacyPilotRouteCandidateEnabled("SR_Breakout");
      g_srRuntimeStates[i].enabled = srEnabled;
      g_srRuntimeStates[i].active = false;
      g_srRuntimeStates[i].runtimeLabel = srEnabled ? (IsLegacyPilotRouteLiveEnabled("SR_Breakout") ? "ON" : "CAND") : "PORT";
      g_srRuntimeStates[i].status = srEnabled ? "WAIT_SIGNAL" : "NO_DATA";
      g_srRuntimeStates[i].adaptiveState = IsLegacyPilotRouteLiveEnabled("SR_Breakout") ? "CAUTION" : "CANDIDATE";
      g_srRuntimeStates[i].adaptiveReason = srEnabled
         ? "SR_Breakout M15 route ported from MT4; live entry requires EnablePilotSRM15Live plus the non-RSI legacy authorization tag"
         : "MT5 SR_Breakout route is disabled";
      g_srRuntimeStates[i].riskMultiplier = IsLegacyPilotRouteLiveEnabled("SR_Breakout") ? 1.0 : 0.0;
      g_srRuntimeStates[i].score = 0.0;
      g_srRuntimeStates[i].reason = srEnabled ? "Waiting for first M15 SR evaluation" : "SR_Breakout route disabled";
   }
}

int CurrentServerDayKey()
{
   datetime serverNow = TimeTradeServer();
   if(serverNow <= 0)
      serverNow = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(serverNow, dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
}

void ResetPilotTelemetryForIndex(int index, int dayKey)
{
   if(index < 0 || index >= ArraySize(g_pilotTelemetry))
      return;

   g_pilotTelemetry[index].dayKey = dayKey;
   g_pilotTelemetry[index].evaluationPasses = 0;
   g_pilotTelemetry[index].signalHits = 0;
   g_pilotTelemetry[index].waitBarSkips = 0;
   g_pilotTelemetry[index].noCrossMisses = 0;
   g_pilotTelemetry[index].spreadBlocks = 0;
   g_pilotTelemetry[index].sessionBlocks = 0;
   g_pilotTelemetry[index].newsBlocks = 0;
   g_pilotTelemetry[index].newsFiltered = 0;
   g_pilotTelemetry[index].manualBlocks = 0;
   g_pilotTelemetry[index].portfolioBlocks = 0;
   g_pilotTelemetry[index].inPositionBlocks = 0;
   g_pilotTelemetry[index].regimeBlocks = 0;
   g_pilotTelemetry[index].cooldownBlocks = 0;
   g_pilotTelemetry[index].startupBlocks = 0;
   g_pilotTelemetry[index].orderSent = 0;
   g_pilotTelemetry[index].orderFailed = 0;
   g_pilotTelemetry[index].lastEvalTime = 0;
   g_pilotTelemetry[index].lastSignalTime = 0;
   g_pilotTelemetry[index].lastOrderTime = 0;
   g_pilotTelemetry[index].lastStatus = "NO_DATA";
   g_pilotTelemetry[index].lastReason = "Waiting for first pilot evaluation";
   g_pilotTelemetry[index].lastDirection = 0;
}

void EnsurePilotTelemetryState()
{
   int symbolCount = ArraySize(g_symbols);
   if(ArraySize(g_pilotTelemetry) != symbolCount)
      ArrayResize(g_pilotTelemetry, symbolCount);

   int dayKey = CurrentServerDayKey();
   for(int i = 0; i < symbolCount; i++)
   {
      if(g_pilotTelemetry[i].dayKey != dayKey)
         ResetPilotTelemetryForIndex(i, dayKey);
   }
}

void UpdatePilotTelemetrySnapshot(int index, string status, string reason, int direction = 0)
{
   if(index < 0 || index >= ArraySize(g_pilotTelemetry))
      return;

   g_pilotTelemetry[index].lastStatus = status;
   g_pilotTelemetry[index].lastReason = reason;
   g_pilotTelemetry[index].lastDirection = direction;
}

string BuildPilotTelemetryJson(int index)
{
   if(index < 0 || index >= ArraySize(g_pilotTelemetry))
      return "{}";

   PilotTelemetrySnapshot telemetry = g_pilotTelemetry[index];
   string json = "{";
   json += "\"dayKey\": " + IntegerToString(telemetry.dayKey) + ", ";
   json += "\"evaluationPasses\": " + IntegerToString(telemetry.evaluationPasses) + ", ";
   json += "\"signalHits\": " + IntegerToString(telemetry.signalHits) + ", ";
   json += "\"waitBarSkips\": " + IntegerToString(telemetry.waitBarSkips) + ", ";
   json += "\"noCrossMisses\": " + IntegerToString(telemetry.noCrossMisses) + ", ";
   json += "\"spreadBlocks\": " + IntegerToString(telemetry.spreadBlocks) + ", ";
   json += "\"sessionBlocks\": " + IntegerToString(telemetry.sessionBlocks) + ", ";
   json += "\"newsBlocks\": " + IntegerToString(telemetry.newsBlocks) + ", ";
   json += "\"newsFiltered\": " + IntegerToString(telemetry.newsFiltered) + ", ";
   json += "\"manualBlocks\": " + IntegerToString(telemetry.manualBlocks) + ", ";
   json += "\"portfolioBlocks\": " + IntegerToString(telemetry.portfolioBlocks) + ", ";
   json += "\"inPositionBlocks\": " + IntegerToString(telemetry.inPositionBlocks) + ", ";
   json += "\"regimeBlocks\": " + IntegerToString(telemetry.regimeBlocks) + ", ";
   json += "\"cooldownBlocks\": " + IntegerToString(telemetry.cooldownBlocks) + ", ";
   json += "\"startupBlocks\": " + IntegerToString(telemetry.startupBlocks) + ", ";
   json += "\"orderSent\": " + IntegerToString(telemetry.orderSent) + ", ";
   json += "\"orderFailed\": " + IntegerToString(telemetry.orderFailed) + ", ";
   json += "\"lastEvalTime\": \"" + JsonEscape(FormatDateTime(telemetry.lastEvalTime, true)) + "\", ";
   json += "\"lastSignalTime\": \"" + JsonEscape(FormatDateTime(telemetry.lastSignalTime, true)) + "\", ";
   json += "\"lastOrderTime\": \"" + JsonEscape(FormatDateTime(telemetry.lastOrderTime, true)) + "\", ";
   json += "\"lastStatus\": \"" + JsonEscape(telemetry.lastStatus) + "\", ";
   json += "\"lastReason\": \"" + JsonEscape(telemetry.lastReason) + "\", ";
   json += "\"lastDirection\": " + IntegerToString(telemetry.lastDirection);
   json += "}";
   return json;
}

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   StringReplace(value, "\r", "\\r");
   StringReplace(value, "\n", "\\n");
   StringReplace(value, "\t", "\\t");
   return value;
}

string JsonBool(bool value)
{
   return value ? "true" : "false";
}

string FormatDateTime(datetime value, bool withSeconds = false)
{
   if(value <= 0)
      return "";
   int flags = TIME_DATE | TIME_MINUTES;
   if(withSeconds)
      flags |= TIME_SECONDS;
   return TimeToString(value, flags);
}

string FormatNumber(double value, int digits)
{
   if(!MathIsValidNumber(value))
      value = 0.0;
   return DoubleToString(value, digits);
}

double CalcSpreadPips(string symbol, double bid, double ask)
{
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(point <= 0.0)
      return 0.0;
   double spreadPoints = (ask - bid) / point;
   if(digits == 3 || digits == 5)
      spreadPoints /= 10.0;
   return spreadPoints;
}

void AppendEntryDiagnosticReason(string &items, string code, string label, string detail)
{
   if(StringLen(items) > 0)
      items += ", ";
   items += "{\"code\": \"" + JsonEscape(code) + "\", ";
   items += "\"label\": \"" + JsonEscape(label) + "\", ";
   items += "\"detail\": \"" + JsonEscape(detail) + "\"}";
}

string EntryDiagnosticStateZh(string state)
{
   if(state == "READY_BUY_SIGNAL")
      return "RSI 买入信号已触发，等待 EA 守门执行";
   if(state == "WAITING_RSI_SIGNAL")
      return "RSI 买入路线已恢复，等待 H1 信号";
   if(state == "WAITING_NEXT_BAR")
      return "等待下一根已收盘 K 线确认";
   if(state == "SELL_SIDE_DEMOTED")
      return "RSI 卖出侧已降级，只等待买入";
   if(state == "ROUTE_DISABLED")
      return "RSI 路线未启用";
   if(state == "ROUTE_NOT_LIVE")
      return "RSI 路线未恢复实盘观察";
   if(state == "PERMISSION_BLOCKED")
      return "交易权限未通过";
   if(state == "KILL_SWITCH")
      return "熔断保护中";
   if(state == "PORTFOLIO_FULL")
      return "EA 仓位容量已满";
   if(state == "SYMBOL_POSITION_FULL")
      return "USDJPY EA 单品种仓位已满";
   if(state == "MANUAL_POSITION_BLOCK")
      return "人工持仓占用该品种";
   if(state == "LOSS_COOLDOWN")
      return "亏损冷却中";
   if(state == "NEWS_BLOCK")
      return "新闻过滤阻断中";
   if(state == "STARTUP_GUARD")
      return "启动保护中";
   if(state == "SESSION_CLOSED")
      return "当前不在 EA 入场时段";
   if(state == "SPREAD_BLOCK")
      return "点差超过 EA 入场限制";
   if(state == "SYMBOL_MISSING")
      return "USDJPY 品种未登记";
   if(state == "BUY_SIGNAL_READY")
      return "买入信号已就绪";
   return "等待 EA 自身信号";
}

bool IsPilotManagedPosition(string comment, long magic)
{
   if(IsPilotStrategyComment(comment))
      return true;
   if(PilotRequireStrategyCommentForManagedPosition)
      return false;
   return (magic == PilotMagic);
}

int CountPilotPositions(string symbol = "")
{
   int count = 0;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      string posSymbol = PositionGetString(POSITION_SYMBOL);
      if(StringLen(symbol) > 0 && posSymbol != symbol)
         continue;
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(IsPilotManagedPosition(comment, magic))
         count++;
   }
   return count;
}

bool HasManualPositionOnSymbol(string symbol)
{
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      string posSymbol = PositionGetString(POSITION_SYMBOL);
      if(posSymbol != symbol)
         continue;
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         return true;
   }
   return false;
}

double SumPilotFloatingProfit()
{
   double totalProfit = 0.0;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;
      totalProfit += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return totalProfit;
}

void UpdatePilotClosedStats()
{
   g_pilotRealizedLossToday = 0.0;
   g_pilotConsecutiveLosses = 0;
   g_pilotLatestConsecutiveLossTime = 0;
   g_pilotLatestConsecutiveLossNet = 0.0;
   g_pilotConsecutiveLossPauseRemainingMinutes = 0;
   g_pilotConsecutiveLossPauseExpired = false;

   datetime nowServer = CurrentServerTime();
   MqlDateTime parts;
   TimeToStruct(nowServer, parts);
   parts.hour = 0;
   parts.min = 0;
   parts.sec = 0;
   datetime dayStart = StructToTime(parts);

   if(!HistorySelect(dayStart - 86400 * 7, nowServer))
      return;

   int total = HistoryDealsTotal();
   bool streakLocked = false;
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      long dealType = HistoryDealGetInteger(ticket, DEAL_TYPE);
      if(dealType != DEAL_TYPE_BUY && dealType != DEAL_TYPE_SELL)
         continue;
      long entryType = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      if(!IsExitDeal(entryType))
         continue;
      string comment = HistoryDealGetString(ticket, DEAL_COMMENT);
      long magic = HistoryDealGetInteger(ticket, DEAL_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;

      double net = HistoryDealGetDouble(ticket, DEAL_PROFIT) +
                   HistoryDealGetDouble(ticket, DEAL_SWAP) +
                   HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      datetime dealTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
      if(dealTime >= dayStart && net < 0.0)
         g_pilotRealizedLossToday += MathAbs(net);

      if(!streakLocked)
      {
         if(net < 0.0)
         {
            g_pilotConsecutiveLosses++;
            if(g_pilotLatestConsecutiveLossTime <= 0)
            {
               g_pilotLatestConsecutiveLossTime = dealTime;
               g_pilotLatestConsecutiveLossNet = net;
            }
         }
         else
            streakLocked = true;
      }
   }
}

bool GetLatestPilotClosedTradeForSymbol(string symbol, datetime &closeTime, double &netProfit)
{
   closeTime = 0;
   netProfit = 0.0;

   datetime nowServer = CurrentServerTime();
   if(!HistorySelect(nowServer - 86400 * 7, nowServer))
      return false;

   int total = HistoryDealsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      long dealType = HistoryDealGetInteger(ticket, DEAL_TYPE);
      if(dealType != DEAL_TYPE_BUY && dealType != DEAL_TYPE_SELL)
         continue;
      long entryType = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      if(!IsExitDeal(entryType))
         continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL) != symbol)
         continue;

      string comment = HistoryDealGetString(ticket, DEAL_COMMENT);
      long magic = HistoryDealGetInteger(ticket, DEAL_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;

      closeTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
      netProfit = HistoryDealGetDouble(ticket, DEAL_PROFIT) +
                  HistoryDealGetDouble(ticket, DEAL_SWAP) +
                  HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      return true;
   }

   return false;
}

bool PilotLossCooldownActive(string symbol, string &reason)
{
   reason = "";
   if(PilotLossCooldownMinutes <= 0)
      return false;

   datetime closeTime = 0;
   double netProfit = 0.0;
   if(!GetLatestPilotClosedTradeForSymbol(symbol, closeTime, netProfit))
      return false;
   if(netProfit >= 0.0 || closeTime <= 0)
      return false;

   int elapsedMinutes = (int)((CurrentServerTime() - closeTime) / 60);
   if(elapsedMinutes >= PilotLossCooldownMinutes)
      return false;

   int minutesLeft = PilotLossCooldownMinutes - elapsedMinutes;
   reason = "Loss cooldown active for " + IntegerToString(minutesLeft) +
            "m after " + FormatNumber(MathAbs(netProfit), 2) + " USC stopout";
   return true;
}

bool PilotConsecutiveLossPauseActive(string &reason)
{
   reason = "";
   g_pilotConsecutiveLossPauseRemainingMinutes = 0;
   g_pilotConsecutiveLossPauseExpired = false;

   if(PilotMaxConsecutiveLosses <= 0)
      return false;
   if(g_pilotConsecutiveLosses < PilotMaxConsecutiveLosses)
      return false;

   if(PilotConsecutiveLossPauseMinutes <= 0 || g_pilotLatestConsecutiveLossTime <= 0)
   {
      reason = "Consecutive loss limit reached";
      return true;
   }

   int elapsedMinutes = (int)((CurrentServerTime() - g_pilotLatestConsecutiveLossTime) / 60);
   if(elapsedMinutes < 0)
      elapsedMinutes = 0;

   int minutesLeft = PilotConsecutiveLossPauseMinutes - elapsedMinutes;
   if(minutesLeft > 0)
   {
      g_pilotConsecutiveLossPauseRemainingMinutes = minutesLeft;
      reason = "Consecutive loss pause active for " + IntegerToString(minutesLeft) +
               "m after " + IntegerToString(g_pilotConsecutiveLosses) +
               " pilot losses";
      return true;
   }

   g_pilotConsecutiveLossPauseExpired = true;
   return false;
}

bool IsPilotSessionOpen()
{
   if(!PilotRestrictSession)
      return true;
   MqlDateTime parts;
   TimeToStruct(CurrentServerTime(), parts);
   int hour = parts.hour;
   if(PilotSessionStartHour <= PilotSessionEndHour)
      return (hour >= PilotSessionStartHour && hour <= PilotSessionEndHour);
   return (hour >= PilotSessionStartHour || hour <= PilotSessionEndHour);
}

bool IsNewPilotBar(string symbol, ENUM_TIMEFRAMES timeframe, int symbolIndex)
{
   datetime barTime = iTime(symbol, timeframe, 0);
   if(barTime <= 0)
      return false;
   if(g_lastPilotBarTime[symbolIndex] == 0)
   {
      g_lastPilotBarTime[symbolIndex] = barTime;
      return false;
   }
   if(barTime != g_lastPilotBarTime[symbolIndex])
   {
      g_lastPilotBarTime[symbolIndex] = barTime;
      return true;
   }
   return false;
}

bool IsNewTrackedBar(string symbol, ENUM_TIMEFRAMES timeframe, int symbolIndex, datetime &lastBarTimes[])
{
   if(symbolIndex < 0 || symbolIndex >= ArraySize(lastBarTimes))
      return false;
   datetime barTime = iTime(symbol, timeframe, 0);
   if(barTime <= 0)
      return false;
   if(lastBarTimes[symbolIndex] == 0)
   {
      lastBarTimes[symbolIndex] = barTime;
      return false;
   }
   if(barTime != lastBarTimes[symbolIndex])
   {
      lastBarTimes[symbolIndex] = barTime;
      return true;
   }
   return false;
}

string PilotEvalCodeLabel(int evalCode)
{
   if(evalCode == PILOT_EVAL_NOT_ENOUGH_BARS) return "NOT_ENOUGH_BARS";
   if(evalCode == PILOT_EVAL_TICK_UNAVAILABLE) return "TICK_UNAVAILABLE";
   if(evalCode == PILOT_EVAL_SPREAD_BLOCK) return "SPREAD_BLOCK";
   if(evalCode == PILOT_EVAL_SESSION_BLOCK) return "SESSION_BLOCK";
   if(evalCode == PILOT_EVAL_INDICATOR_NOT_READY) return "INDICATOR_NOT_READY";
   if(evalCode == PILOT_EVAL_TREND_NOT_READY) return "TREND_NOT_READY";
   if(evalCode == PILOT_EVAL_ATR_UNAVAILABLE) return "ATR_UNAVAILABLE";
   if(evalCode == PILOT_EVAL_RANGE_BLOCK) return "RANGE_BLOCK";
   if(evalCode == PILOT_EVAL_SIGNAL_BUY) return "SIGNAL_BUY";
   if(evalCode == PILOT_EVAL_SIGNAL_SELL) return "SIGNAL_SELL";
   if(evalCode == PILOT_EVAL_NO_CROSS) return "NO_CROSS";
   return "NONE";
}

string PilotDirectionLabel(int direction)
{
   if(direction > 0) return "BUY";
   if(direction < 0) return "SELL";
   return "NONE";
}

string BoolLabel(bool value)
{
   return value ? "Y" : "N";
}

string ShadowSignalLedgerHeader()
{
   return "EventId,LabelTimeLocal,LabelTimeServer,EventBarTime,Symbol,Strategy,Timeframe,SignalStatus,SignalDirection,SignalScore,Regime,Blocker,ExecutionAction,ReferencePrice,SpreadPips,NewsStatus,Reason\r\n";
}

void AppendShadowSignalLedgerRow(string symbol, int symbolIndex, datetime eventBarTime, string signalStatus, int direction, double score, string blocker, string executionAction, string reason)
{
   if(symbolIndex < 0 || symbolIndex >= ArraySize(g_lastShadowLedgerBarTime))
      return;
   if(eventBarTime <= 0)
      eventBarTime = iTime(symbol, PilotSignalTimeframe, 0);
   if(eventBarTime <= 0 || g_lastShadowLedgerBarTime[symbolIndex] == eventBarTime)
      return;

   g_lastShadowLedgerBarTime[symbolIndex] = eventBarTime;

   MqlTick tick;
   ZeroMemory(tick);
   SymbolInfoTick(symbol, tick);
   double referencePrice = 0.0;
   if(direction > 0)
      referencePrice = tick.ask;
   else if(direction < 0)
      referencePrice = tick.bid;
   else if(tick.bid > 0.0 && tick.ask > 0.0)
      referencePrice = (tick.bid + tick.ask) / 2.0;
   double spread = (tick.bid > 0.0 && tick.ask > 0.0) ? CalcSpreadPips(symbol, tick.bid, tick.ask) : 0.0;
   RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotTrendTimeframe, eventBarTime);
   datetime serverClock = CurrentServerTime();
   string eventId = symbol + "-" + TimeframeLabel(PilotSignalTimeframe) + "-" + IntegerToString((int)eventBarTime) + "-" + signalStatus + "-" + executionAction;

   bool exists = FileIsExist("QuantGod_ShadowSignalLedger.csv");
   ResetLastError();
   int handle = FileOpen("QuantGod_ShadowSignalLedger.csv",
                         FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         0, CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("QuantGod MT5 shadow ledger failed to open file. err=", GetLastError());
      return;
   }
   if(!exists || FileSize(handle) <= 0)
      FileWriteString(handle, ShadowSignalLedgerHeader());
   FileSeek(handle, 0, SEEK_END);
   string row = "";
   row += CsvEscape(eventId) + ",";
   row += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
   row += CsvEscape(FormatDateTime(serverClock, true)) + ",";
   row += CsvEscape(FormatDateTime(eventBarTime, true)) + ",";
   row += CsvEscape(symbol) + ",";
   row += CsvEscape("MA_Cross") + ",";
   row += CsvEscape(TimeframeLabel(PilotSignalTimeframe)) + ",";
   row += CsvEscape(signalStatus) + ",";
   row += CsvEscape(PilotDirectionLabel(direction)) + ",";
   row += FormatNumber(score, 1) + ",";
   row += CsvEscape(regime.label) + ",";
   row += CsvEscape(blocker) + ",";
   row += CsvEscape(executionAction) + ",";
   row += FormatNumber(referencePrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   row += FormatNumber(spread, 1) + ",";
   row += CsvEscape(g_newsState.status) + ",";
   row += CsvEscape(reason) + "\r\n";
   FileWriteString(handle, row);
   FileFlush(handle);
   FileClose(handle);
}

void AppendShadowSignalLedgerForCurrentBar(string symbol, int symbolIndex, string signalStatus, int direction, double score, string blocker, string executionAction, string reason)
{
   AppendShadowSignalLedgerRow(symbol, symbolIndex, iTime(symbol, PilotSignalTimeframe, 0), signalStatus, direction, score, blocker, executionAction, reason);
}

void PushShadowSignalRecord(ShadowSignalLedgerRecord &records[], ShadowSignalLedgerRecord &record)
{
   int size = ArraySize(records);
   ArrayResize(records, size + 1);
   records[size] = record;
}

string CsvCellValue(string value)
{
   string cell = TrimString(value);
   int len = StringLen(cell);
   if(len >= 2 &&
      StringGetCharacter(cell, 0) == '"' &&
      StringGetCharacter(cell, len - 1) == '"')
      cell = StringSubstr(cell, 1, len - 2);
   StringReplace(cell, "\"\"", "\"");
   return cell;
}

string ShadowCandidateLedgerHeader()
{
   return "EventId,LabelTimeLocal,LabelTimeServer,EventBarTime,Symbol,CandidateRoute,Timeframe,CandidateDirection,CandidateScore,Regime,ReferencePrice,SpreadPips,NewsStatus,Trigger,Reason\r\n";
}

void AppendShadowCandidateLedgerRowForTimeframe(string symbol, ENUM_TIMEFRAMES routeTimeframe, datetime eventBarTime, string route, int direction, double score, string trigger, string reason)
{
   if(!EnableShadowCandidateRouter || eventBarTime <= 0 || direction == 0)
      return;

   MqlTick tick;
   ZeroMemory(tick);
   if(!SymbolInfoTick(symbol, tick))
      return;

   double referencePrice = (direction > 0) ? tick.ask : tick.bid;
   if(referencePrice <= 0.0)
      return;

   double spread = (tick.bid > 0.0 && tick.ask > 0.0) ? CalcSpreadPips(symbol, tick.bid, tick.ask) : 0.0;
   RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotTrendTimeframe, eventBarTime);
   datetime serverClock = CurrentServerTime();
   string eventId = symbol + "-" + TimeframeLabel(routeTimeframe) + "-" + IntegerToString((int)eventBarTime) + "-" + route + "-" + PilotDirectionLabel(direction);

   bool exists = FileIsExist("QuantGod_ShadowCandidateLedger.csv");
   ResetLastError();
   int handle = FileOpen("QuantGod_ShadowCandidateLedger.csv",
                         FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         0, CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("QuantGod MT5 shadow candidate ledger failed to open file. err=", GetLastError());
      return;
   }
   if(!exists || FileSize(handle) <= 0)
      FileWriteString(handle, ShadowCandidateLedgerHeader());
   FileSeek(handle, 0, SEEK_END);

   string row = "";
   row += CsvEscape(eventId) + ",";
   row += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
   row += CsvEscape(FormatDateTime(serverClock, true)) + ",";
   row += CsvEscape(FormatDateTime(eventBarTime, true)) + ",";
   row += CsvEscape(symbol) + ",";
   row += CsvEscape(route) + ",";
   row += CsvEscape(TimeframeLabel(routeTimeframe)) + ",";
   row += CsvEscape(PilotDirectionLabel(direction)) + ",";
   row += FormatNumber(score, 1) + ",";
   row += CsvEscape(regime.label) + ",";
   row += FormatNumber(referencePrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   row += FormatNumber(spread, 1) + ",";
   row += CsvEscape(g_newsState.status) + ",";
   row += CsvEscape(trigger) + ",";
   row += CsvEscape(reason) + "\r\n";
   FileWriteString(handle, row);
   FileFlush(handle);
   FileClose(handle);
}

void AppendShadowCandidateLedgerRow(string symbol, datetime eventBarTime, string route, int direction, double score, string trigger, string reason)
{
   AppendShadowCandidateLedgerRowForTimeframe(symbol, PilotSignalTimeframe, eventBarTime, route, direction, score, trigger, reason);
}

void AppendUsdJpyTokyoBreakoutShadowRoute(string symbol, datetime eventBarTime, double close1, double open1, double atr1, double pip, double routeSpreadPips, bool lowSpreadForResearch)
{
   if(!EnableUsdJpyTokyoBreakoutShadowResearch || !IsUsdJpySymbol(symbol) || !lowSpreadForResearch || atr1 <= 0.0 || pip <= 0.0)
      return;

   int minute = JstMinuteOfDayFromServerTime(eventBarTime);
   if(minute < 12 * 60 || minute > 18 * 60)
      return;

   int dayKey = JstDayKeyFromServerTime(eventBarTime);
   double boxHigh = 0.0;
   double boxLow = 0.0;
   int samples = 0;
   int bars = Bars(symbol, PERIOD_M15);
   int maxLookback = MathMin(bars - 1, 120);
   for(int shift = 1; shift <= maxLookback; shift++)
   {
      datetime barTime = iTime(symbol, PERIOD_M15, shift);
      if(barTime <= 0)
         continue;
      if(JstDayKeyFromServerTime(barTime) != dayKey)
         continue;
      int barMinute = JstMinuteOfDayFromServerTime(barTime);
      if(barMinute < 9 * 60 || barMinute >= 12 * 60)
         continue;

      double high = iHigh(symbol, PERIOD_M15, shift);
      double low = iLow(symbol, PERIOD_M15, shift);
      if(high <= 0.0 || low <= 0.0)
         continue;
      if(samples == 0)
      {
         boxHigh = high;
         boxLow = low;
      }
      else
      {
         boxHigh = MathMax(boxHigh, high);
         boxLow = MathMin(boxLow, low);
      }
      samples++;
   }

   if(samples < 6 || boxHigh <= boxLow)
      return;

   double boxPips = (boxHigh - boxLow) / pip;
   if(boxPips < 12.0 || boxPips > 75.0)
      return;

   double buffer = MathMax(8.0 * pip, atr1 * 0.15);
   double adx = ADXValue(symbol, PERIOD_M15, 14, 1);
   bool adxPass = (adx != EMPTY_VALUE && adx >= 18.0);
   bool bullishClose = (close1 > open1);
   bool bearishClose = (close1 < open1);

   if(adxPass && close1 > boxHigh + buffer)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_TOKYO_RANGE_BREAKOUT", 1, 74.0,
                                     "JST 09-12 box high breakout, ADX confirmed",
                                     "Shadow-only Tokyo range breakout candidate; never sends live orders");
   else if(adxPass && close1 < boxLow - buffer)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_TOKYO_RANGE_BREAKOUT", -1, 74.0,
                                     "JST 09-12 box low breakdown, ADX confirmed",
                                     "Shadow-only Tokyo range breakout candidate; never sends live orders");
   else if(close1 > boxHigh - buffer * 0.50 && bullishClose)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_TOKYO_RANGE_BREAKOUT", 1, 52.0,
                                     "Near Tokyo box high with bullish pressure",
                                     "Shadow-only pre-breakout sample for faster research collection");
   else if(close1 < boxLow + buffer * 0.50 && bearishClose)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_TOKYO_RANGE_BREAKOUT", -1, 52.0,
                                     "Near Tokyo box low with bearish pressure",
                                     "Shadow-only pre-breakout sample for faster research collection");
}

void AppendUsdJpyNightReversionShadowRoute(string symbol, datetime eventBarTime, double close1, double open1, double atr1, string regimeLabel, bool lowSpreadForResearch)
{
   if(!EnableUsdJpyNightReversionShadowResearch || !IsUsdJpySymbol(symbol) || !lowSpreadForResearch || atr1 <= 0.0)
      return;

   int minute = JstMinuteOfDayFromServerTime(eventBarTime);
   bool nightWindow = (minute >= 21 * 60 || minute <= 8 * 60 + 30);
   if(!nightWindow)
      return;

   double rsi1 = RSIValue(symbol, PERIOD_M15, 14, 1);
   double upperBand = BandsValue(symbol, PERIOD_M15, 20, 2.0, 1, 1);
   double lowerBand = BandsValue(symbol, PERIOD_M15, 20, 2.0, 2, 1);
   double adx = ADXValue(symbol, PERIOD_M15, 14, 1);
   if(rsi1 <= 0.0 || upperBand <= 0.0 || lowerBand <= 0.0 || adx == EMPTY_VALUE || adx >= 20.0)
      return;
   if(!(regimeLabel == "RANGE" || regimeLabel == "RANGE_TIGHT"))
      return;

   bool bullishClose = (close1 >= open1);
   bool bearishClose = (close1 <= open1);
   if(close1 <= lowerBand && rsi1 <= 35.0 && bullishClose)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_NIGHT_REVERSION_SAFE", 1, 64.0,
                                     "Low-volatility night lower-band reversion setup",
                                     "Shadow-only night reversion candidate; opportunity grade only");
   else if(close1 >= upperBand && rsi1 >= 65.0 && bearishClose)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_NIGHT_REVERSION_SAFE", -1, 64.0,
                                     "Low-volatility night upper-band reversion setup",
                                     "Shadow-only night reversion candidate; opportunity grade only");
   else if(close1 <= lowerBand + atr1 * 0.15 && rsi1 <= 40.0)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_NIGHT_REVERSION_SAFE", 1, 50.0,
                                     "Soft night lower-band reversion pressure",
                                     "Shadow-only soft reversion sample for faster outcome labeling");
   else if(close1 >= upperBand - atr1 * 0.15 && rsi1 >= 60.0)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_NIGHT_REVERSION_SAFE", -1, 50.0,
                                     "Soft night upper-band reversion pressure",
                                     "Shadow-only soft reversion sample for faster outcome labeling");
}

void AppendUsdJpyH4PullbackShadowRoute(string symbol, datetime eventBarTime, double close1, double open1, double high1, double low1, double atr1, double fast1, double slow1, double pip, bool lowSpreadForResearch)
{
   if(!EnableUsdJpyH4PullbackShadowResearch || !IsUsdJpySymbol(symbol) || !lowSpreadForResearch || atr1 <= 0.0 || pip <= 0.0)
      return;
   if(Bars(symbol, PERIOD_H4) < 205)
      return;

   double h4Close1 = iClose(symbol, PERIOD_H4, 1);
   double h4Ema50 = MAValue(symbol, PERIOD_H4, 50, 1, MODE_EMA);
   double h4Ema50Prev = MAValue(symbol, PERIOD_H4, 50, 2, MODE_EMA);
   double h4Ema200 = MAValue(symbol, PERIOD_H4, 200, 1, MODE_EMA);
   double rsi1 = RSIValue(symbol, PERIOD_M15, 14, 1);
   double rsi2 = RSIValue(symbol, PERIOD_M15, 14, 2);
   if(h4Close1 <= 0.0 || h4Ema50 <= 0.0 || h4Ema200 <= 0.0 || rsi1 <= 0.0)
      return;

   bool h4LongTrend = (h4Close1 > h4Ema200 && h4Ema50 > h4Ema200 && h4Ema50 >= h4Ema50Prev);
   bool h4ShortTrend = (h4Close1 < h4Ema200 && h4Ema50 < h4Ema200 && h4Ema50 <= h4Ema50Prev);
   bool bullishClose = (close1 > open1);
   bool bearishClose = (close1 < open1);
   bool longPullback = (low1 <= slow1 + atr1 * 0.30 && close1 >= fast1 && bullishClose &&
                        ((rsi1 >= 38.0 && rsi1 <= 62.0) || (rsi2 > 0.0 && rsi1 > rsi2 + 2.0)));
   bool shortPullback = (high1 >= slow1 - atr1 * 0.30 && close1 <= fast1 && bearishClose &&
                         ((rsi1 >= 38.0 && rsi1 <= 62.0) || (rsi2 > 0.0 && rsi1 < rsi2 - 2.0)));

   if(h4LongTrend && longPullback)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_H4_TREND_PULLBACK", 1, 70.0,
                                     "H4 uptrend with M15 pullback recovery",
                                     "Shadow-only H4 trend pullback candidate; requires backtest and governance before live");
   else if(h4ShortTrend && shortPullback)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_H4_TREND_PULLBACK", -1, 70.0,
                                     "H4 downtrend with M15 pullback rejection",
                                     "Shadow-only H4 trend pullback candidate; requires backtest and governance before live");
}

void AppendShadowCandidateRoutesForBar(string symbol, int symbolIndex, datetime eventBarTime)
{
   if(!EnableShadowCandidateRouter ||
      symbolIndex < 0 ||
      symbolIndex >= ArraySize(g_lastShadowCandidateLedgerBarTime) ||
      eventBarTime <= 0 ||
      g_lastShadowCandidateLedgerBarTime[symbolIndex] == eventBarTime)
      return;

   g_lastShadowCandidateLedgerBarTime[symbolIndex] = eventBarTime;

   int signalBars = Bars(symbol, PilotSignalTimeframe);
   int trendBars = Bars(symbol, PilotTrendTimeframe);
   if(signalBars < MathMax(PilotSlowMAPeriod + 6, PilotATRPeriod + 5) ||
      trendBars < PilotTrendMAPeriod + 5)
      return;

   double trend1 = MAValue(symbol, PilotTrendTimeframe, PilotTrendMAPeriod, 1, MODE_SMA);
   double trendClose1 = iClose(symbol, PilotTrendTimeframe, 1);
   double atr1 = ATRValue(symbol, PilotSignalTimeframe, PilotATRPeriod, 1);
   double fast1 = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, 1, MODE_EMA);
   double fast2 = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, 2, MODE_EMA);
   double slow1 = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, 1, MODE_EMA);
   double slow2 = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, 2, MODE_EMA);
   double close1 = iClose(symbol, PilotSignalTimeframe, 1);
   double open1 = iOpen(symbol, PilotSignalTimeframe, 1);
   double high1 = iHigh(symbol, PilotSignalTimeframe, 1);
   double low1 = iLow(symbol, PilotSignalTimeframe, 1);
   if(trend1 == EMPTY_VALUE || fast1 == EMPTY_VALUE || fast2 == EMPTY_VALUE ||
      slow1 == EMPTY_VALUE || slow2 == EMPTY_VALUE || atr1 <= 0.0 ||
      trendClose1 <= 0.0 || close1 <= 0.0 || open1 <= 0.0 || high1 <= 0.0 || low1 <= 0.0)
      return;

   bool buyTrend = (trendClose1 > trend1);
   bool sellTrend = (trendClose1 < trend1);
   bool bullishStructure = (fast1 > slow1 && fast2 > slow2);
   bool bearishStructure = (fast1 < slow1 && fast2 < slow2);
   bool freshCross = false;
   int maxShift = MathMax(1, PilotCrossLookbackBars);
   for(int shift = 1; shift <= maxShift; shift++)
   {
      double fastCurr = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, shift, MODE_EMA);
      double fastPrev = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, shift + 1, MODE_EMA);
      double slowCurr = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, shift, MODE_EMA);
      double slowPrev = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, shift + 1, MODE_EMA);
      if(fastCurr == EMPTY_VALUE || fastPrev == EMPTY_VALUE ||
         slowCurr == EMPTY_VALUE || slowPrev == EMPTY_VALUE)
         continue;
      if((fastPrev <= slowPrev && fastCurr > slowCurr) ||
         (fastPrev >= slowPrev && fastCurr < slowCurr))
      {
         freshCross = true;
         break;
      }
   }

   double pip = PipSize(symbol);
   if(pip <= 0.0)
      return;
   double fastDistanceAtr = MathAbs(close1 - fast1) / atr1;
   bool bullishClose = (close1 > open1);
   bool bearishClose = (close1 < open1);
   bool fastSlopeUp = (fast1 >= fast2);
   bool fastSlopeDown = (fast1 <= fast2);
   bool slowSlopeUp = (slow1 >= slow2);
   bool slowSlopeDown = (slow1 <= slow2);
   RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotTrendTimeframe, eventBarTime);
   MqlTick routeTick;
   ZeroMemory(routeTick);
   double routeSpreadPips = 0.0;
   bool lowSpreadForResearch = false;
   if(SymbolInfoTick(symbol, routeTick) && routeTick.bid > 0.0 && routeTick.ask > 0.0)
   {
      routeSpreadPips = CalcSpreadPips(symbol, routeTick.bid, routeTick.ask);
      lowSpreadForResearch = (routeSpreadPips <= PilotMaxSpreadPips);
   }

   AppendUsdJpyTokyoBreakoutShadowRoute(symbol, eventBarTime, close1, open1, atr1, pip, routeSpreadPips, lowSpreadForResearch);
   AppendUsdJpyNightReversionShadowRoute(symbol, eventBarTime, close1, open1, atr1, regime.label, lowSpreadForResearch);
   AppendUsdJpyH4PullbackShadowRoute(symbol, eventBarTime, close1, open1, high1, low1, atr1, fast1, slow1, pip, lowSpreadForResearch);

   if(!freshCross && buyTrend && bullishStructure && close1 >= fast1 && fastDistanceAtr <= 1.20)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "TREND_CONT_NO_CROSS", 1, 66.0,
                                     "H1 uptrend, EMA structure aligned, no fresh cross",
                                     "Shadow-only trend continuation without fresh crossover");
   else if(!freshCross && sellTrend && bearishStructure && close1 <= fast1 && fastDistanceAtr <= 1.20)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "TREND_CONT_NO_CROSS", -1, 66.0,
                                     "H1 downtrend, EMA structure aligned, no fresh cross",
                                     "Shadow-only trend continuation without fresh crossover");
   else if(!freshCross && buyTrend && fast1 > slow1 && fastSlopeUp && slowSlopeUp && close1 >= slow1 && fastDistanceAtr <= 1.80)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "TREND_CONT_NO_CROSS", 1, 59.0,
                                     "Soft H1 uptrend continuation pressure without fresh cross",
                                     "Shadow-only soft trend continuation sample; live MA_Cross gate unchanged");
   else if(!freshCross && sellTrend && fast1 < slow1 && fastSlopeDown && slowSlopeDown && close1 <= slow1 && fastDistanceAtr <= 1.80)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "TREND_CONT_NO_CROSS", -1, 59.0,
                                     "Soft H1 downtrend continuation pressure without fresh cross",
                                     "Shadow-only soft trend continuation sample; live MA_Cross gate unchanged");

   bool isUsdJpy = (StringFind(symbol, "USDJPY") >= 0);
   double touchTolerance = atr1 * 0.25;
   bool usdJpyRangePullback = (isUsdJpy && lowSpreadForResearch &&
                               (regime.label == "RANGE" || regime.label == "RANGE_TIGHT") &&
                               MathAbs(close1 - fast1) <= atr1 * 0.85);
   if(isUsdJpy && lowSpreadForResearch && buyTrend && bullishStructure && low1 <= fast1 + touchTolerance && close1 >= fast1)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_PULLBACK_BOUNCE", 1, 68.0,
                                     "USDJPY pullback touched fast EMA and closed back above it",
                                     "Shadow-only USDJPY pullback/bounce candidate");
   else if(isUsdJpy && lowSpreadForResearch && sellTrend && bearishStructure && high1 >= fast1 - touchTolerance && close1 <= fast1)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_PULLBACK_BOUNCE", -1, 68.0,
                                     "USDJPY pullback touched fast EMA and closed back below it",
                                     "Shadow-only USDJPY pullback/bounce candidate");
   else if(usdJpyRangePullback && bullishClose && close1 >= fast1 && fastSlopeUp)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_PULLBACK_BOUNCE", 1, 61.0,
                                     "USDJPY low-spread range pullback reclaimed fast EMA",
                                     "Shadow-only Manual Alpha inspired USDJPY pullback sample; live entries unchanged");
   else if(usdJpyRangePullback && bearishClose && close1 <= fast1 && fastSlopeDown)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "USDJPY_PULLBACK_BOUNCE", -1, 61.0,
                                     "USDJPY low-spread range pullback rejected fast EMA",
                                     "Shadow-only Manual Alpha inspired USDJPY pullback sample; live entries unchanged");

   if(regime.label == "RANGE" || regime.label == "RANGE_TIGHT")
   {
      if(lowSpreadForResearch && close1 > fast1 && fast1 >= fast2 && bullishClose && fastDistanceAtr <= 0.90)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "RANGE_SOFT", 1, 46.0,
                                        "Low-spread range with tighter bullish drift confirmation",
                                        "Deprioritized shadow-only range-soft candidate after weak post-outcomes; live range guard unchanged");
      else if(lowSpreadForResearch && close1 < fast1 && fast1 <= fast2 && bearishClose && fastDistanceAtr <= 0.90)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "RANGE_SOFT", -1, 46.0,
                                        "Low-spread range with tighter bearish drift confirmation",
                                        "Deprioritized shadow-only range-soft candidate after weak post-outcomes; live range guard unchanged");
   }

   double rsi1 = RSIValue(symbol, PilotSignalTimeframe, 14, 1);
   double rsi2 = RSIValue(symbol, PilotSignalTimeframe, 14, 2);
   bool rsiResearchRegime = (lowSpreadForResearch && (regime.label == "RANGE" || regime.label == "RANGE_TIGHT"));
   if(rsi1 > 0.0 && rsiResearchRegime)
   {
      if(rsi1 <= 30.0 && close1 >= open1)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "RSI_REVERSAL_SHADOW", 1, 60.0,
                                        "Low-spread range RSI oversold with bullish close",
                                        "Shadow-only RSI reversal candidate with stricter research filters");
      else if(rsi1 >= 70.0 && close1 <= open1)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "RSI_REVERSAL_SHADOW", -1, 60.0,
                                        "Low-spread range RSI overbought with bearish close",
                                        "Shadow-only RSI reversal candidate with stricter research filters");
      else if((rsi1 <= 38.0 && bullishClose && close1 >= fast1 - atr1 * 0.20) ||
              (rsi2 > 0.0 && rsi2 <= 32.0 && rsi1 > rsi2 + 2.5 && close1 >= fast1 - atr1 * 0.25))
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "RSI_REVERSAL_SHADOW", 1, 55.0,
                                        "Low-spread range soft RSI bullish reversal pressure",
                                        "Shadow-only soft RSI reversal sample with stricter filters; live entries unchanged");
      else if((rsi1 >= 62.0 && bearishClose && close1 <= fast1 + atr1 * 0.20) ||
              (rsi2 > 0.0 && rsi2 >= 68.0 && rsi1 < rsi2 - 2.5 && close1 <= fast1 + atr1 * 0.25))
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "RSI_REVERSAL_SHADOW", -1, 55.0,
                                        "Low-spread range soft RSI bearish reversal pressure",
                                        "Shadow-only soft RSI reversal sample with stricter filters; live entries unchanged");
   }

   double upperBand = BandsValue(symbol, PilotSignalTimeframe, 20, 2.0, 1, 1);
   double lowerBand = BandsValue(symbol, PilotSignalTimeframe, 20, 2.0, 2, 1);
   if(rsi1 > 0.0 && upperBand > 0.0 && lowerBand > 0.0)
   {
      if(close1 <= lowerBand && rsi1 <= 35.0)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "BB_TRIPLE_SHADOW", 1, 60.0,
                                        "Close near lower Bollinger band with weak RSI",
                                        "Shadow-only Bollinger/RSI reversal candidate");
      else if(close1 >= upperBand && rsi1 >= 65.0)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "BB_TRIPLE_SHADOW", -1, 60.0,
                                        "Close near upper Bollinger band with strong RSI",
                                        "Shadow-only Bollinger/RSI reversal candidate");
   }

   double macdMain1 = MACDValue(symbol, PilotSignalTimeframe, 12, 26, 9, 0, 1);
   double macdSignal1 = MACDValue(symbol, PilotSignalTimeframe, 12, 26, 9, 1, 1);
   double macdMain2 = MACDValue(symbol, PilotSignalTimeframe, 12, 26, 9, 0, 2);
   double macdSignal2 = MACDValue(symbol, PilotSignalTimeframe, 12, 26, 9, 1, 2);
   double macdMain3 = MACDValue(symbol, PilotSignalTimeframe, 12, 26, 9, 0, 3);
   double macdSignal3 = MACDValue(symbol, PilotSignalTimeframe, 12, 26, 9, 1, 3);
   if(macdMain1 != EMPTY_VALUE && macdSignal1 != EMPTY_VALUE &&
      macdMain2 != EMPTY_VALUE && macdSignal2 != EMPTY_VALUE)
   {
      double macdHist1 = macdMain1 - macdSignal1;
      double macdHist2 = macdMain2 - macdSignal2;
      double macdHist3 = (macdMain3 != EMPTY_VALUE && macdSignal3 != EMPTY_VALUE) ? macdMain3 - macdSignal3 : macdHist2;
      if(lowSpreadForResearch && buyTrend && bullishClose && macdMain2 <= macdSignal2 && macdMain1 > macdSignal1 && close1 >= fast1)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "MACD_MOMENTUM_TURN", 1, 49.0,
                                        "Low-spread MACD upward cross with trend and EMA confirmation",
                                        "Deprioritized shadow-only MACD momentum candidate after weak post-outcomes");
      else if(lowSpreadForResearch && sellTrend && bearishClose && macdMain2 >= macdSignal2 && macdMain1 < macdSignal1 && close1 <= fast1)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "MACD_MOMENTUM_TURN", -1, 49.0,
                                        "Low-spread MACD downward cross with trend and EMA confirmation",
                                        "Deprioritized shadow-only MACD momentum candidate after weak post-outcomes");
      else if(lowSpreadForResearch && buyTrend && bullishClose && macdHist1 > macdHist2 && macdHist2 > macdHist3 && close1 >= fast1)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "MACD_MOMENTUM_TURN", 1, 44.0,
                                        "Low-spread MACD histogram rising with trend confirmation",
                                        "Deprioritized shadow-only soft MACD sample; live entries unchanged");
      else if(lowSpreadForResearch && sellTrend && bearishClose && macdHist1 < macdHist2 && macdHist2 < macdHist3 && close1 <= fast1)
         AppendShadowCandidateLedgerRow(symbol, eventBarTime, "MACD_MOMENTUM_TURN", -1, 44.0,
                                        "Low-spread MACD histogram falling with trend confirmation",
                                        "Deprioritized shadow-only soft MACD sample; live entries unchanged");
   }

   int breakoutLookback = 12;
   double priorHigh = 0.0;
   double priorLow = 0.0;
   for(int shift = 2; shift <= breakoutLookback + 1; shift++)
   {
      double high = iHigh(symbol, PilotSignalTimeframe, shift);
      double low = iLow(symbol, PilotSignalTimeframe, shift);
      if(high <= 0.0 || low <= 0.0)
         continue;
      if(priorHigh <= 0.0 || high > priorHigh)
         priorHigh = high;
      if(priorLow <= 0.0 || low < priorLow)
         priorLow = low;
   }
   double breakoutBuffer = MathMax(2.0 * pip, atr1 * 0.10);
   double candleMid = (high1 + low1) * 0.5;
   if(lowSpreadForResearch && buyTrend && bullishClose && priorHigh > 0.0 && close1 > priorHigh + breakoutBuffer)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "SR_BREAKOUT_SHADOW", 1, 47.0,
                                     "Low-spread trend-aligned close broke above resistance with buffer",
                                     "Deprioritized shadow-only support/resistance breakout candidate after weak post-outcomes");
   else if(lowSpreadForResearch && sellTrend && bearishClose && priorLow > 0.0 && close1 < priorLow - breakoutBuffer)
      AppendShadowCandidateLedgerRow(symbol, eventBarTime, "SR_BREAKOUT_SHADOW", -1, 47.0,
                                     "Low-spread trend-aligned close broke below support with buffer",
                                     "Deprioritized shadow-only support/resistance breakout candidate after weak post-outcomes");
}

bool LoadShadowSignalLedgerRecords(ShadowSignalLedgerRecord &records[])
{
   ArrayResize(records, 0);
   if(!FileIsExist("QuantGod_ShadowSignalLedger.csv"))
      return false;

   ResetLastError();
   int handle = FileOpen("QuantGod_ShadowSignalLedger.csv",
                         FILE_READ | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         ',', CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("QuantGod MT5 shadow outcome failed to open source ledger. err=", GetLastError());
      return false;
   }

   for(int h = 0; h < 17 && !FileIsEnding(handle); h++)
      FileReadString(handle);

   while(!FileIsEnding(handle))
   {
      ShadowSignalLedgerRecord record;
      record.eventId = CsvCellValue(FileReadString(handle));
      if(FileIsEnding(handle) && StringLen(record.eventId) == 0)
         break;
      FileReadString(handle); // LabelTimeLocal
      FileReadString(handle); // LabelTimeServer
      string eventBarTime = CsvCellValue(FileReadString(handle));
      record.eventBarTime = StringToTime(eventBarTime);
      record.symbol = CsvCellValue(FileReadString(handle));
      record.strategy = CsvCellValue(FileReadString(handle));
      record.timeframe = CsvCellValue(FileReadString(handle));
      record.signalStatus = CsvCellValue(FileReadString(handle));
      record.signalDirection = CsvCellValue(FileReadString(handle));
      FileReadString(handle); // SignalScore
      FileReadString(handle); // Regime
      record.blocker = CsvCellValue(FileReadString(handle));
      record.executionAction = CsvCellValue(FileReadString(handle));
      record.referencePrice = StringToDouble(CsvCellValue(FileReadString(handle)));
      FileReadString(handle); // SpreadPips
      FileReadString(handle); // NewsStatus
      FileReadString(handle); // Reason

      if(StringLen(record.eventId) > 0 &&
         StringLen(record.symbol) > 0 &&
         record.eventBarTime > 0 &&
         record.referencePrice > 0.0)
         PushShadowSignalRecord(records, record);
   }

   FileClose(handle);
   return (ArraySize(records) > 0);
}

bool CalculateShadowOutcome(string symbol, datetime eventBarTime, int horizonBars, double referencePrice,
                            double &futureClose, double &longClosePips, double &shortClosePips,
                            double &longMfePips, double &longMaePips, double &shortMfePips, double &shortMaePips)
{
   futureClose = 0.0;
   longClosePips = 0.0;
   shortClosePips = 0.0;
   longMfePips = 0.0;
   longMaePips = 0.0;
   shortMfePips = 0.0;
   shortMaePips = 0.0;
   if(horizonBars <= 0 || StringLen(symbol) == 0 || eventBarTime <= 0 || referencePrice <= 0.0)
      return false;

   double pip = PipSize(symbol);
   if(pip <= 0.0)
      return false;

   int eventShift = iBarShift(symbol, PilotSignalTimeframe, eventBarTime, true);
   if(eventShift < 0)
      return false;

   int futureShift = eventShift - horizonBars + 1;
   if(futureShift < 1)
      return false;

   futureClose = iClose(symbol, PilotSignalTimeframe, futureShift);
   if(futureClose <= 0.0)
      return false;

   double maxHigh = referencePrice;
   double minLow = referencePrice;
   for(int shift = eventShift; shift >= futureShift; shift--)
   {
      double high = iHigh(symbol, PilotSignalTimeframe, shift);
      double low = iLow(symbol, PilotSignalTimeframe, shift);
      if(high > 0.0 && high > maxHigh)
         maxHigh = high;
      if(low > 0.0 && low < minLow)
         minLow = low;
   }

   longClosePips = (futureClose - referencePrice) / pip;
   shortClosePips = (referencePrice - futureClose) / pip;
   longMfePips = (maxHigh - referencePrice) / pip;
   longMaePips = (referencePrice - minLow) / pip;
   shortMfePips = (referencePrice - minLow) / pip;
   shortMaePips = (maxHigh - referencePrice) / pip;
   return true;
}

string ShadowDirectionalOutcome(string direction, double longClosePips, double shortClosePips)
{
   double neutral = MathMax(0.1, ShadowOutcomeNeutralPips);
   string normalizedDirection = ToUpperString(direction);
   if(normalizedDirection == "BUY")
   {
      if(longClosePips >= neutral) return "WIN";
      if(longClosePips <= -neutral) return "LOSS";
      return "FLAT";
   }
   if(normalizedDirection == "SELL")
   {
      if(shortClosePips >= neutral) return "WIN";
      if(shortClosePips <= -neutral) return "LOSS";
      return "FLAT";
   }
   if(longClosePips >= neutral && longClosePips >= shortClosePips)
      return "LONG_OPPORTUNITY";
   if(shortClosePips >= neutral && shortClosePips > longClosePips)
      return "SHORT_OPPORTUNITY";
   return "NEUTRAL_OPPORTUNITY";
}

string ShadowBestOpportunity(double longClosePips, double shortClosePips)
{
   double neutral = MathMax(0.1, ShadowOutcomeNeutralPips);
   if(longClosePips >= neutral && longClosePips >= shortClosePips)
      return "LONG";
   if(shortClosePips >= neutral && shortClosePips > longClosePips)
      return "SHORT";
   return "NEUTRAL";
}

string BuildShadowOutcomeLedgerCsv()
{
   string csv = "EventId,OutcomeLabelTimeLocal,OutcomeLabelTimeServer,EventBarTime,Symbol,Strategy,Timeframe,SignalStatus,SignalDirection,Blocker,ExecutionAction,ReferencePrice,HorizonBars,HorizonMinutes,FutureClose,LongClosePips,ShortClosePips,LongMFEPips,LongMAEPips,ShortMFEPips,ShortMAEPips,DirectionalOutcome,BestOpportunity,OutcomeReason\r\n";
   ShadowSignalLedgerRecord records[];
   if(!EnableShadowOutcomeLedger || !LoadShadowSignalLedgerRecords(records))
      return csv;

   int total = ArraySize(records);
   int maxRows = MathMax(1, ShadowOutcomeMaxSourceRows);
   int start = MathMax(0, total - maxRows);
   int horizons[3] = {1, 2, 4};
   datetime serverClock = CurrentServerTime();
   int periodSeconds = PeriodSeconds(PilotSignalTimeframe);
   if(periodSeconds <= 0)
      periodSeconds = 60 * 15;

   for(int i = start; i < total; i++)
   {
      for(int h = 0; h < 3; h++)
      {
         int horizonBars = horizons[h];
         double futureClose = 0.0;
         double longClosePips = 0.0;
         double shortClosePips = 0.0;
         double longMfePips = 0.0;
         double longMaePips = 0.0;
         double shortMfePips = 0.0;
         double shortMaePips = 0.0;
         if(!CalculateShadowOutcome(records[i].symbol,
                                    records[i].eventBarTime,
                                    horizonBars,
                                    records[i].referencePrice,
                                    futureClose,
                                    longClosePips,
                                    shortClosePips,
                                    longMfePips,
                                    longMaePips,
                                    shortMfePips,
                                    shortMaePips))
            continue;

         int digits = (int)SymbolInfoInteger(records[i].symbol, SYMBOL_DIGITS);
         string directionalOutcome = ShadowDirectionalOutcome(records[i].signalDirection, longClosePips, shortClosePips);
         string bestOpportunity = ShadowBestOpportunity(longClosePips, shortClosePips);
         string reason = "Shadow-only post outcome label; does not alter live order gating";

         csv += CsvEscape(records[i].eventId) + ",";
         csv += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
         csv += CsvEscape(FormatDateTime(serverClock, true)) + ",";
         csv += CsvEscape(FormatDateTime(records[i].eventBarTime, true)) + ",";
         csv += CsvEscape(records[i].symbol) + ",";
         csv += CsvEscape(records[i].strategy) + ",";
         csv += CsvEscape(records[i].timeframe) + ",";
         csv += CsvEscape(records[i].signalStatus) + ",";
         csv += CsvEscape(records[i].signalDirection) + ",";
         csv += CsvEscape(records[i].blocker) + ",";
         csv += CsvEscape(records[i].executionAction) + ",";
         csv += FormatNumber(records[i].referencePrice, digits) + ",";
         csv += IntegerToString(horizonBars) + ",";
         csv += IntegerToString((periodSeconds * horizonBars) / 60) + ",";
         csv += FormatNumber(futureClose, digits) + ",";
         csv += FormatNumber(longClosePips, 1) + ",";
         csv += FormatNumber(shortClosePips, 1) + ",";
         csv += FormatNumber(longMfePips, 1) + ",";
         csv += FormatNumber(longMaePips, 1) + ",";
         csv += FormatNumber(shortMfePips, 1) + ",";
         csv += FormatNumber(shortMaePips, 1) + ",";
         csv += CsvEscape(directionalOutcome) + ",";
         csv += CsvEscape(bestOpportunity) + ",";
         csv += CsvEscape(reason) + "\r\n";
      }
   }

   return csv;
}

void PushShadowCandidateRecord(ShadowCandidateLedgerRecord &records[], ShadowCandidateLedgerRecord &record)
{
   int size = ArraySize(records);
   ArrayResize(records, size + 1);
   records[size] = record;
}

bool LoadShadowCandidateLedgerRecords(ShadowCandidateLedgerRecord &records[])
{
   ArrayResize(records, 0);
   if(!FileIsExist("QuantGod_ShadowCandidateLedger.csv"))
      return false;

   ResetLastError();
   int handle = FileOpen("QuantGod_ShadowCandidateLedger.csv",
                         FILE_READ | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         ',', CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("QuantGod MT5 shadow candidate outcome failed to open source ledger. err=", GetLastError());
      return false;
   }

   for(int h = 0; h < 15 && !FileIsEnding(handle); h++)
      FileReadString(handle);

   while(!FileIsEnding(handle))
   {
      ShadowCandidateLedgerRecord record;
      record.eventId = CsvCellValue(FileReadString(handle));
      if(FileIsEnding(handle) && StringLen(record.eventId) == 0)
         break;
      FileReadString(handle); // LabelTimeLocal
      FileReadString(handle); // LabelTimeServer
      string eventBarTime = CsvCellValue(FileReadString(handle));
      record.eventBarTime = StringToTime(eventBarTime);
      record.symbol = CsvCellValue(FileReadString(handle));
      record.candidateRoute = CsvCellValue(FileReadString(handle));
      record.timeframe = CsvCellValue(FileReadString(handle));
      record.direction = CsvCellValue(FileReadString(handle));
      record.score = StringToDouble(CsvCellValue(FileReadString(handle)));
      record.regime = CsvCellValue(FileReadString(handle));
      record.referencePrice = StringToDouble(CsvCellValue(FileReadString(handle)));
      FileReadString(handle); // SpreadPips
      FileReadString(handle); // NewsStatus
      record.trigger = CsvCellValue(FileReadString(handle));
      record.reason = CsvCellValue(FileReadString(handle));

      if(StringLen(record.eventId) > 0 &&
         StringLen(record.symbol) > 0 &&
         record.eventBarTime > 0 &&
         record.referencePrice > 0.0)
         PushShadowCandidateRecord(records, record);
   }

   FileClose(handle);
   return (ArraySize(records) > 0);
}

string BuildShadowCandidateOutcomeLedgerCsv()
{
   string csv = "EventId,OutcomeLabelTimeLocal,OutcomeLabelTimeServer,EventBarTime,Symbol,CandidateRoute,Timeframe,CandidateDirection,CandidateScore,Regime,ReferencePrice,HorizonBars,HorizonMinutes,FutureClose,LongClosePips,ShortClosePips,LongMFEPips,LongMAEPips,ShortMFEPips,ShortMAEPips,DirectionalOutcome,BestOpportunity,OutcomeReason\r\n";
   ShadowCandidateLedgerRecord records[];
   if(!EnableShadowCandidateRouter || !LoadShadowCandidateLedgerRecords(records))
      return csv;

   int total = ArraySize(records);
   int maxRows = MathMax(1, ShadowCandidateMaxSourceRows);
   int start = MathMax(0, total - maxRows);
   int horizons[3] = {1, 2, 4};
   datetime serverClock = CurrentServerTime();
   int periodSeconds = PeriodSeconds(PilotSignalTimeframe);
   if(periodSeconds <= 0)
      periodSeconds = 60 * 15;

   for(int i = start; i < total; i++)
   {
      for(int h = 0; h < 3; h++)
      {
         int horizonBars = horizons[h];
         double futureClose = 0.0;
         double longClosePips = 0.0;
         double shortClosePips = 0.0;
         double longMfePips = 0.0;
         double longMaePips = 0.0;
         double shortMfePips = 0.0;
         double shortMaePips = 0.0;
         if(!CalculateShadowOutcome(records[i].symbol,
                                    records[i].eventBarTime,
                                    horizonBars,
                                    records[i].referencePrice,
                                    futureClose,
                                    longClosePips,
                                    shortClosePips,
                                    longMfePips,
                                    longMaePips,
                                    shortMfePips,
                                    shortMaePips))
            continue;

         int digits = (int)SymbolInfoInteger(records[i].symbol, SYMBOL_DIGITS);
         string directionalOutcome = ShadowDirectionalOutcome(records[i].direction, longClosePips, shortClosePips);
         string bestOpportunity = ShadowBestOpportunity(longClosePips, shortClosePips);
         string reason = "Shadow candidate post outcome label; does not alter live order gating";

         csv += CsvEscape(records[i].eventId) + ",";
         csv += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
         csv += CsvEscape(FormatDateTime(serverClock, true)) + ",";
         csv += CsvEscape(FormatDateTime(records[i].eventBarTime, true)) + ",";
         csv += CsvEscape(records[i].symbol) + ",";
         csv += CsvEscape(records[i].candidateRoute) + ",";
         csv += CsvEscape(records[i].timeframe) + ",";
         csv += CsvEscape(records[i].direction) + ",";
         csv += FormatNumber(records[i].score, 1) + ",";
         csv += CsvEscape(records[i].regime) + ",";
         csv += FormatNumber(records[i].referencePrice, digits) + ",";
         csv += IntegerToString(horizonBars) + ",";
         csv += IntegerToString((periodSeconds * horizonBars) / 60) + ",";
         csv += FormatNumber(futureClose, digits) + ",";
         csv += FormatNumber(longClosePips, 1) + ",";
         csv += FormatNumber(shortClosePips, 1) + ",";
         csv += FormatNumber(longMfePips, 1) + ",";
         csv += FormatNumber(longMaePips, 1) + ",";
         csv += FormatNumber(shortMfePips, 1) + ",";
         csv += FormatNumber(shortMaePips, 1) + ",";
         csv += CsvEscape(directionalOutcome) + ",";
         csv += CsvEscape(bestOpportunity) + ",";
         csv += CsvEscape(reason) + "\r\n";
      }
   }

   return csv;
}

string PilotStatusJson(const StrategyStatusSnapshot &state)
{
   string json = "{";
   json += "\"enabled\": " + JsonBool(state.enabled) + ", ";
   json += "\"active\": " + JsonBool(state.active) + ", ";
   json += "\"runtimeLabel\": \"" + JsonEscape(state.runtimeLabel) + "\", ";
   json += "\"status\": \"" + JsonEscape(state.status) + "\", ";
   json += "\"score\": " + FormatNumber(state.score, 1) + ", ";
   json += "\"reason\": \"" + JsonEscape(state.reason) + "\", ";
   json += "\"adaptiveState\": \"" + JsonEscape(state.adaptiveState) + "\", ";
   json += "\"adaptiveReason\": \"" + JsonEscape(state.adaptiveReason) + "\", ";
   json += "\"riskMultiplier\": " + FormatNumber(state.riskMultiplier, 2);
   json += "}";
   return json;
}

string PilotAggregateJson(string scopeSymbol)
{
   int positions = CountPilotPositions(scopeSymbol);
   string json = "{";
   json += "\"enabled\": " + JsonBool(IsPilotLiveMode() && EnablePilotMA) + ", ";
   json += "\"active\": " + JsonBool((IsPilotLiveMode() && EnablePilotMA) && !g_pilotKillSwitch) + ", ";
   json += "\"scopeSymbol\": \"" + JsonEscape(scopeSymbol) + "\", ";
   json += "\"state\": \"" + JsonEscape(g_pilotKillSwitch ? "COOLDOWN" : "CAUTION") + "\", ";
   json += "\"riskMultiplier\": " + FormatNumber((IsPilotLiveMode() && EnablePilotMA) ? 1.0 : 0.0, 2) + ", ";
   json += "\"sampleTrades\": 0, ";
   json += "\"sampleWindowTrades\": 0, ";
   json += "\"winRate\": 0.0, ";
   json += "\"profitFactor\": 0.00, ";
   json += "\"avgNet\": 0.00, ";
   json += "\"netProfit\": 0.00, ";
   json += "\"disabledUntil\": \"\", ";
   json += "\"reason\": \"" + JsonEscape(g_pilotKillSwitch ? g_pilotKillReason : "MT5 0.01 live pilot: M15 trigger, H1 trend filter, 5-bar cross plus 24-bar pullback continuation, range guard, post-loss cooldown, USDJPY news filter") + "\", ";
   json += "\"positions\": " + IntegerToString(positions) + ", ";
   json += "\"portfolioPositions\": " + IntegerToString(CountPilotPositions());
   json += "}";
   return json;
}

string LegacyPilotAggregateJson(string strategyKey, string scopeSymbol)
{
   int symbolIndex = FindSymbolIndex(scopeSymbol);
   StrategyStatusSnapshot state;
   bool hasState = false;
   if(strategyKey == "RSI_Reversal" && symbolIndex >= 0 && symbolIndex < ArraySize(g_rsiRuntimeStates))
   {
      state = g_rsiRuntimeStates[symbolIndex];
      hasState = true;
   }
   else if(strategyKey == "BB_Triple" && symbolIndex >= 0 && symbolIndex < ArraySize(g_bbRuntimeStates))
   {
      state = g_bbRuntimeStates[symbolIndex];
      hasState = true;
   }
   else if(strategyKey == "MACD_Divergence" && symbolIndex >= 0 && symbolIndex < ArraySize(g_macdRuntimeStates))
   {
      state = g_macdRuntimeStates[symbolIndex];
      hasState = true;
   }
   else if(strategyKey == "SR_Breakout" && symbolIndex >= 0 && symbolIndex < ArraySize(g_srRuntimeStates))
   {
      state = g_srRuntimeStates[symbolIndex];
      hasState = true;
   }

   bool candidateEnabled = IsLegacyPilotRouteCandidateEnabled(strategyKey);
   bool inScope = (symbolIndex >= 0) && LegacyPilotRouteInScope(strategyKey, scopeSymbol);
   bool enabled = candidateEnabled && inScope;
   bool liveEnabled = enabled && IsLegacyPilotRouteLiveEnabled(strategyKey);
   string aggregateState = hasState ? state.adaptiveState : (liveEnabled ? "CAUTION" : "CANDIDATE");
   string aggregateReason = hasState ? state.reason :
      (enabled ? "MT4 legacy route is ported as candidate/backtest first; non-RSI live entry requires explicit route switch plus authorization tag"
               : "MT4 legacy route is disabled or out of scope for this symbol");

   string json = "{";
   json += "\"enabled\": " + JsonBool(enabled) + ", ";
   json += "\"active\": " + JsonBool(enabled && hasState && state.active && !g_pilotKillSwitch) + ", ";
   json += "\"scopeSymbol\": \"" + JsonEscape(scopeSymbol) + "\", ";
   json += "\"state\": \"" + JsonEscape(g_pilotKillSwitch ? "COOLDOWN" : aggregateState) + "\", ";
   json += "\"riskMultiplier\": " + FormatNumber((enabled && hasState) ? state.riskMultiplier : 0.0, 2) + ", ";
   json += "\"sampleTrades\": 0, ";
   json += "\"sampleWindowTrades\": 0, ";
   json += "\"winRate\": 0.0, ";
   json += "\"profitFactor\": 0.00, ";
   json += "\"avgNet\": 0.00, ";
   json += "\"netProfit\": 0.00, ";
   json += "\"disabledUntil\": \"\", ";
   json += "\"reason\": \"" + JsonEscape(g_pilotKillSwitch ? g_pilotKillReason : aggregateReason) + "\", ";
   json += "\"positions\": " + IntegerToString(CountPilotPositions(scopeSymbol)) + ", ";
   json += "\"portfolioPositions\": " + IntegerToString(CountPilotPositions());
   json += "}";
   return json;
}

string LegacyPilotAggregateScopeSymbol(string strategyKey, string fallbackSymbol)
{
   if(FindSymbolIndex(fallbackSymbol) >= 0 && LegacyPilotRouteInScope(strategyKey, fallbackSymbol))
      return fallbackSymbol;

   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      if(LegacyPilotRouteInScope(strategyKey, g_symbols[i]))
         return g_symbols[i];
   }

   return fallbackSymbol;
}

bool EvaluatePilotMASignal(string symbol, int symbolIndex, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode)
{
   direction = 0;
   score = 0.0;
   reason = "Waiting for next evaluation";
   slPrice = 0.0;
   tpPrice = 0.0;
   evalCode = PILOT_EVAL_NONE;
   int signalBars = Bars(symbol, PilotSignalTimeframe);
   int trendBars = Bars(symbol, PilotTrendTimeframe);
   if(signalBars < MathMax(PilotSlowMAPeriod + PilotCrossLookbackBars + 5, PilotATRPeriod + 5) ||
      trendBars < PilotTrendMAPeriod + 5)
   {
      reason = "Not enough bars for M15/H1 pilot";
      evalCode = PILOT_EVAL_NOT_ENOUGH_BARS;
      return false;
   }
   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
   {
      reason = "Tick data unavailable";
      evalCode = PILOT_EVAL_TICK_UNAVAILABLE;
      return false;
   }
   double spread = CalcSpreadPips(symbol, tick.bid, tick.ask);
   if(spread > PilotMaxSpreadPips)
   {
      reason = "Spread above pilot limit";
      evalCode = PILOT_EVAL_SPREAD_BLOCK;
      return false;
   }
   if(!IsPilotSessionOpen())
   {
      reason = "Outside pilot trading session";
      evalCode = PILOT_EVAL_SESSION_BLOCK;
      return false;
   }
   double trend1 = MAValue(symbol, PilotTrendTimeframe, PilotTrendMAPeriod, 1, MODE_SMA);
   double trendClose1 = iClose(symbol, PilotTrendTimeframe, 1);
   double atr1 = ATRValue(symbol, PilotSignalTimeframe, PilotATRPeriod, 1);
   double fast1 = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, 1, MODE_EMA);
   double fast2 = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, 2, MODE_EMA);
   double slow1 = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, 1, MODE_EMA);
   double slow2 = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, 2, MODE_EMA);
   double close1 = iClose(symbol, PilotSignalTimeframe, 1);
   double low1 = iLow(symbol, PilotSignalTimeframe, 1);
   double high1 = iHigh(symbol, PilotSignalTimeframe, 1);
   bool buyCross = false;
   bool sellCross = false;
   bool recentBullCross = false;
   bool recentBearCross = false;
   int buyCrossShift = -1;
   int sellCrossShift = -1;
   int recentBullCrossShift = -1;
   int recentBearCrossShift = -1;
   int maxShift = MathMax(1, PilotCrossLookbackBars);
   int continuationMaxShift = MathMax(maxShift, MathMax(4, PilotContinuationLookbackBars));
   for(int shift = 1; shift <= continuationMaxShift; shift++)
   {
      double fastCurr = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, shift, MODE_EMA);
      double fastPrev = MAValue(symbol, PilotSignalTimeframe, PilotFastMAPeriod, shift + 1, MODE_EMA);
      double slowCurr = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, shift, MODE_EMA);
      double slowPrev = MAValue(symbol, PilotSignalTimeframe, PilotSlowMAPeriod, shift + 1, MODE_EMA);
      if(fastCurr == EMPTY_VALUE || fastPrev == EMPTY_VALUE ||
         slowCurr == EMPTY_VALUE || slowPrev == EMPTY_VALUE)
      {
         reason = "Indicator buffers not ready";
         evalCode = PILOT_EVAL_INDICATOR_NOT_READY;
         return false;
      }
      bool bullishCross = (fastPrev <= slowPrev && fastCurr > slowCurr);
      bool bearishCross = (fastPrev >= slowPrev && fastCurr < slowCurr);
      if(!recentBullCross && bullishCross)
      {
         recentBullCross = true;
         recentBullCrossShift = shift;
      }
      if(!recentBearCross && bearishCross)
      {
         recentBearCross = true;
         recentBearCrossShift = shift;
      }
      if(shift > maxShift)
         continue;
      if(!buyCross && bullishCross)
      {
         buyCross = true;
         buyCrossShift = shift;
      }
      if(!sellCross && bearishCross)
      {
         sellCross = true;
         sellCrossShift = shift;
      }
   }

   if(trend1 == EMPTY_VALUE || trendClose1 == 0.0 ||
      fast1 == EMPTY_VALUE || fast2 == EMPTY_VALUE ||
      slow1 == EMPTY_VALUE || slow2 == EMPTY_VALUE ||
      close1 == 0.0 || low1 == 0.0 || high1 == 0.0)
   {
      reason = "Trend filter not ready";
      evalCode = PILOT_EVAL_TREND_NOT_READY;
      return false;
   }
   if(atr1 <= 0.0)
   {
      reason = "ATR unavailable";
      evalCode = PILOT_EVAL_ATR_UNAVAILABLE;
      return false;
   }

    RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotTrendTimeframe, 0);
    if(PilotBlockRangeEntries &&
       (regime.label == "RANGE" || regime.label == "RANGE_TIGHT"))
    {
       reason = "MA_Cross blocked in " + regime.label + " regime";
       evalCode = PILOT_EVAL_RANGE_BLOCK;
       return false;
    }

   bool buyTrend = (trendClose1 > trend1);
   bool sellTrend = (trendClose1 < trend1);
   bool bullishStructure = (fast1 > slow1 && fast2 > slow2);
   bool bearishStructure = (fast1 < slow1 && fast2 < slow2);
   double touchTolerance = atr1 * 0.20;
   double slowGuardTolerance = atr1 * 0.10;
   bool buyPullbackTouch = (low1 <= fast1 + touchTolerance);
   bool buyPullbackHeld = (low1 >= slow1 - slowGuardTolerance && close1 >= fast1);
   bool sellPullbackTouch = (high1 >= fast1 - touchTolerance);
   bool sellPullbackHeld = (high1 <= slow1 + slowGuardTolerance && close1 <= fast1);
   if(buyCross && buyTrend)
   {
      direction = 1;
      score = 100.0 - (double)(buyCrossShift - 1) * 10.0;
      double stopDistance = atr1 * PilotATRMulitplierSL;
      slPrice = NormalizeDouble(tick.ask - stopDistance, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      tpPrice = NormalizeDouble(tick.ask + stopDistance * PilotRewardRatio, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      reason = "M15 bullish crossover within lookback, H1 trend confirmed";
      evalCode = PILOT_EVAL_SIGNAL_BUY;
      return true;
   }
   if(sellCross && sellTrend)
   {
      direction = -1;
      score = 100.0 - (double)(sellCrossShift - 1) * 10.0;
      double stopDistance = atr1 * PilotATRMulitplierSL;
      slPrice = NormalizeDouble(tick.bid + stopDistance, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      tpPrice = NormalizeDouble(tick.bid - stopDistance * PilotRewardRatio, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      reason = "M15 bearish crossover within lookback, H1 trend confirmed";
      evalCode = PILOT_EVAL_SIGNAL_SELL;
      return true;
   }
   if(recentBullCross && recentBullCrossShift > maxShift &&
      buyTrend && bullishStructure && buyPullbackTouch && buyPullbackHeld)
   {
      direction = 1;
      score = MathMax(62.0, 84.0 - (double)(recentBullCrossShift - maxShift) * 4.0);
      double stopDistance = atr1 * PilotATRMulitplierSL;
      slPrice = NormalizeDouble(tick.ask - stopDistance, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      tpPrice = NormalizeDouble(tick.ask + stopDistance * PilotRewardRatio, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      reason = "M15 bullish continuation after pullback, H1 trend confirmed";
      evalCode = PILOT_EVAL_SIGNAL_BUY;
      return true;
   }
   if(recentBearCross && recentBearCrossShift > maxShift &&
      sellTrend && bearishStructure && sellPullbackTouch && sellPullbackHeld)
   {
      direction = -1;
      score = MathMax(62.0, 84.0 - (double)(recentBearCrossShift - maxShift) * 4.0);
      double stopDistance = atr1 * PilotATRMulitplierSL;
      slPrice = NormalizeDouble(tick.bid + stopDistance, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      tpPrice = NormalizeDouble(tick.bid - stopDistance * PilotRewardRatio, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      reason = "M15 bearish continuation after pullback, H1 trend confirmed";
      evalCode = PILOT_EVAL_SIGNAL_SELL;
      return true;
   }
   score = ((buyTrend || sellTrend) ? 55.0 : 25.0);
   reason = "H1 trend exists but no fresh crossover or healthy pullback continuation";
   evalCode = PILOT_EVAL_NO_CROSS;
   return false;
}

ENUM_TIMEFRAMES LegacyPilotRouteTimeframe(string strategyKey)
{
   if(strategyKey == "RSI_Reversal")
      return PilotRsiTimeframe;
   if(strategyKey == "BB_Triple")
      return PilotBBTimeframe;
   if(strategyKey == "MACD_Divergence")
      return PilotMacdTimeframe;
   if(strategyKey == "SR_Breakout")
      return PilotSRTimeframe;
   return PilotSignalTimeframe;
}

string LegacyPilotRouteName(string strategyKey)
{
   if(strategyKey == "RSI_Reversal")
      return "USDJPY_RSI_H1_LIVE_CANDIDATE";
   if(strategyKey == "BB_Triple")
      return "BB_TRIPLE_H1_LEGACY_CANDIDATE";
   if(strategyKey == "MACD_Divergence")
      return "MACD_DIVERGENCE_H1_LEGACY_CANDIDATE";
   if(strategyKey == "SR_Breakout")
      return "SR_BREAKOUT_M15_LEGACY_CANDIDATE";
   return "LEGACY_CANDIDATE";
}

bool LegacyPilotRouteInScope(string strategyKey, string symbol)
{
   if(strategyKey == "RSI_Reversal")
      return IsUsdJpySymbol(symbol);
   return true;
}

bool IsDowntrendRegimeLabel(string regime)
{
   string upper = ToUpperString(regime);
   return (StringFind(upper, "DOWN") >= 0);
}

bool IsUptrendRegimeLabel(string regime)
{
   string upper = ToUpperString(regime);
   return (upper == "TREND_UP" || upper == "TREND_EXP_UP");
}

bool CommonLegacyPilotPrecheck(string symbol, ENUM_TIMEFRAMES timeframe, int minBars, MqlTick &tick, string &reason, int &evalCode)
{
   if(Bars(symbol, timeframe) < minBars)
   {
      reason = "Not enough bars for " + TimeframeLabel(timeframe) + " legacy pilot route";
      evalCode = PILOT_EVAL_NOT_ENOUGH_BARS;
      return false;
   }
   if(!SymbolInfoTick(symbol, tick) || tick.bid <= 0.0 || tick.ask <= 0.0)
   {
      reason = "Tick data unavailable";
      evalCode = PILOT_EVAL_TICK_UNAVAILABLE;
      return false;
   }
   double spread = CalcSpreadPips(symbol, tick.bid, tick.ask);
   if(spread > PilotMaxSpreadPips)
   {
      reason = "Spread above pilot limit";
      evalCode = PILOT_EVAL_SPREAD_BLOCK;
      return false;
   }
   if(!IsPilotSessionOpen())
   {
      reason = "Outside pilot trading session";
      evalCode = PILOT_EVAL_SESSION_BLOCK;
      return false;
   }
   return true;
}

bool EvaluatePilotRsiH1Signal(string symbol, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode, string &trigger)
{
   direction = 0;
   score = 0.0;
   reason = "Waiting for USDJPY RSI_Reversal H1 evaluation";
   trigger = "";
   slPrice = 0.0;
   tpPrice = 0.0;
   evalCode = PILOT_EVAL_NONE;

   if(!IsUsdJpySymbol(symbol))
   {
      reason = "RSI_Reversal H1 live-candidate route is scoped to USDJPY";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }

   MqlTick tick;
   ZeroMemory(tick);
   int effectiveRsiPeriod = PilotRsiPeriod;
   double effectiveRsiOversold = AutonomousPatchEffectiveRsiBuyBand((double)PilotRsiOversold);
   double effectiveCrossbackThreshold = AutonomousPatchEffectiveRsiCrossbackThreshold(MathMax(0.0, PilotRsiCrossbackThreshold));
   if(!CommonLegacyPilotPrecheck(symbol, PilotRsiTimeframe, MathMax(30, effectiveRsiPeriod + 5), tick, reason, evalCode))
      return false;

   double rsi1 = RSIValue(symbol, PilotRsiTimeframe, effectiveRsiPeriod, 1);
   double rsi2 = RSIValue(symbol, PilotRsiTimeframe, effectiveRsiPeriod, 2);
   double lowerBand = BandsValue(symbol, PilotRsiTimeframe, 20, 2.0, 2, 1);
   double upperBand = BandsValue(symbol, PilotRsiTimeframe, 20, 2.0, 1, 1);
   double close1 = iClose(symbol, PilotRsiTimeframe, 1);
   double atr1 = ATRValue(symbol, PilotRsiTimeframe, PilotATRPeriod, 1);
   if(rsi1 <= 0.0 || rsi2 <= 0.0 || lowerBand <= 0.0 || upperBand <= 0.0 || close1 <= 0.0 || atr1 <= 0.0)
   {
      reason = "RSI H1 indicator buffers not ready";
      evalCode = PILOT_EVAL_INDICATOR_NOT_READY;
      return false;
   }

   double crossbackThreshold = MathMax(0.0, effectiveCrossbackThreshold);
   bool exactBuyReversal = (rsi2 < effectiveRsiOversold && rsi1 > effectiveRsiOversold + crossbackThreshold);
   bool exactSellReversal = (rsi2 > PilotRsiOverbought && rsi1 < PilotRsiOverbought - crossbackThreshold);
   bool buyReversal = (rsi1 <= effectiveRsiOversold || exactBuyReversal);
   bool sellReversal = (rsi1 >= PilotRsiOverbought || exactSellReversal);
   double tolerance = MathMax(0.0, PilotRsiBandTolerancePct);
   bool buyBand = (close1 <= lowerBand * (1.0 + tolerance));
   bool sellBand = (close1 >= upperBand * (1.0 - tolerance));
   double buyScore = (double)((buyReversal ? 1 : 0) + (buyBand ? 1 : 0)) / 2.0 * 100.0;
   double sellScore = (double)((sellReversal ? 1 : 0) + (sellBand ? 1 : 0)) / 2.0 * 100.0;
   double stopDistance = atr1 * MathMax(0.5, PilotRsiATRMultiplierSL);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotRsiTimeframe, 0);

   bool sellLiveBlockedAfterReview = (PilotRsiSellLiveBlocked && !MQLInfoInteger(MQL_TESTER));
   if(sellReversal && sellBand && !sellLiveBlockedAfterReview)
   {
      if(PilotRsiBlockSellInUptrend && IsUptrendRegimeLabel(regime.label))
      {
         score = sellScore;
         reason = "RSI H1 SELL blocked in " + regime.label + " regime after live loss review";
         evalCode = PILOT_EVAL_RANGE_BLOCK;
         return false;
      }
      if(PilotRsiRangeTightBuyOnly && IsRangeTightRegimeLabel(regime.label))
      {
         score = sellScore;
         reason = "RSI H1 SELL blocked in RANGE_TIGHT; this regime is buy-only after live loss review";
         evalCode = PILOT_EVAL_RANGE_BLOCK;
         return false;
      }
   }

   if(buyReversal && buyBand)
   {
      direction = 1;
      score = 100.0;
      slPrice = NormalizeDouble(tick.ask - stopDistance, digits);
      tpPrice = NormalizeDouble(tick.ask + stopDistance * PilotRewardRatio, digits);
      trigger = "RSI2 H1 oversold/crossback with lower Bollinger touch";
      reason = "USDJPY RSI_Reversal H1 buy setup ported from MT4";
      if(g_autonomousPatchRuntimeActive)
         reason += " | Agent patch active: rsiBuyBand=" + FormatNumber(effectiveRsiOversold, 1) +
                   " crossback=" + FormatNumber(crossbackThreshold, 2);
      evalCode = PILOT_EVAL_SIGNAL_BUY;
      return true;
   }
   if(sellReversal && sellBand)
   {
      direction = -1;
      score = 100.0;
      slPrice = NormalizeDouble(tick.bid + stopDistance, digits);
      tpPrice = NormalizeDouble(tick.bid - stopDistance * PilotRewardRatio, digits);
      trigger = "RSI2 H1 overbought/crossback with upper Bollinger touch";
      reason = "USDJPY RSI_Reversal H1 sell setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_SELL;
      return true;
   }

   if(buyScore >= sellScore)
   {
      score = buyScore;
      reason = "RSI H1 BUY bias " + FormatNumber(buyScore, 0) + "/100 | reversal=" + BoolLabel(buyReversal) +
               " band=" + BoolLabel(buyBand);
      if(g_autonomousPatchRuntimeActive)
         reason += " | agentPatch rsiBuyBand=" + FormatNumber(effectiveRsiOversold, 1) +
                   " crossback=" + FormatNumber(crossbackThreshold, 2);
   }
   else
   {
      score = sellScore;
      reason = "RSI H1 SELL bias " + FormatNumber(sellScore, 0) + "/100 | reversal=" + BoolLabel(sellReversal) + " band=" + BoolLabel(sellBand);
   }
   evalCode = PILOT_EVAL_NO_CROSS;
   return false;
}

bool EvaluatePilotBBH1Signal(string symbol, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode, string &trigger)
{
   direction = 0;
   score = 0.0;
   reason = "Waiting for BB_Triple H1 evaluation";
   trigger = "";
   slPrice = 0.0;
   tpPrice = 0.0;
   evalCode = PILOT_EVAL_NONE;

   MqlTick tick;
   ZeroMemory(tick);
   if(!CommonLegacyPilotPrecheck(symbol, PilotBBTimeframe, MathMax(PilotBBPeriod + 5, PilotBBRsiPeriod + 5), tick, reason, evalCode))
      return false;

   double close1 = iClose(symbol, PilotBBTimeframe, 1);
   double upperBand = BandsValue(symbol, PilotBBTimeframe, PilotBBPeriod, PilotBBDeviation, 1, 1);
   double lowerBand = BandsValue(symbol, PilotBBTimeframe, PilotBBPeriod, PilotBBDeviation, 2, 1);
   double rsi1 = RSIValue(symbol, PilotBBTimeframe, PilotBBRsiPeriod, 1);
   double rsi2 = RSIValue(symbol, PilotBBTimeframe, PilotBBRsiPeriod, 2);
   double macdMain1 = MACDValue(symbol, PilotBBTimeframe, 12, 26, 9, 0, 1);
   double macdMain2 = MACDValue(symbol, PilotBBTimeframe, 12, 26, 9, 0, 2);
   double macdSignal1 = MACDValue(symbol, PilotBBTimeframe, 12, 26, 9, 1, 1);
   double macdSignal2 = MACDValue(symbol, PilotBBTimeframe, 12, 26, 9, 1, 2);
   double atr1 = ATRValue(symbol, PilotBBTimeframe, PilotATRPeriod, 1);
   if(close1 <= 0.0 || upperBand <= 0.0 || lowerBand <= 0.0 || rsi1 <= 0.0 || rsi2 <= 0.0 || atr1 <= 0.0 ||
      macdMain1 == EMPTY_VALUE || macdMain2 == EMPTY_VALUE || macdSignal1 == EMPTY_VALUE || macdSignal2 == EMPTY_VALUE)
   {
      reason = "BB H1 indicator buffers not ready";
      evalCode = PILOT_EVAL_INDICATOR_NOT_READY;
      return false;
   }

   RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotBBTimeframe, 0);
   bool bbBuySignal = (close1 <= lowerBand * 1.005);
   bool rsiBuySignal = (rsi1 < PilotBBRsiOversold || (rsi2 < PilotBBRsiOversold && rsi1 > PilotBBRsiOversold));
   bool macdBuyConfirm = (macdMain1 > macdSignal1 || (macdMain2 < macdSignal2 && macdMain1 > macdSignal1));
   bool bbSellSignal = (close1 >= upperBand * 0.995);
   bool rsiSellSignal = (rsi1 > PilotBBRsiOverbought || (rsi2 > PilotBBRsiOverbought && rsi1 < PilotBBRsiOverbought));
   bool macdSellConfirm = (macdMain1 < macdSignal1 || (macdMain2 > macdSignal2 && macdMain1 < macdSignal1));
   double buyScore = (double)((bbBuySignal ? 1 : 0) + (rsiBuySignal ? 1 : 0) + (macdBuyConfirm ? 1 : 0)) / 3.0 * 100.0;
   double sellScore = (double)((bbSellSignal ? 1 : 0) + (rsiSellSignal ? 1 : 0) + (macdSellConfirm ? 1 : 0)) / 3.0 * 100.0;
   double stopDistance = atr1 * 2.0;
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   if(StringFind(ToUpperString(symbol), "EURUSD") >= 0 && regime.label == "TREND_EXP_DOWN" && bbBuySignal && rsiBuySignal)
   {
      score = buyScore;
      reason = "EURUSD BB guard skipped buy setup in TREND_EXP_DOWN";
      evalCode = PILOT_EVAL_RANGE_BLOCK;
      return false;
   }
   if(bbBuySignal && rsiBuySignal && !macdBuyConfirm)
   {
      score = buyScore;
      reason = "BB_Triple candidate tightened: buy requires MACD confirmation";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }
   if(bbBuySignal && rsiBuySignal)
   {
      direction = 1;
      score = 100.0;
      slPrice = NormalizeDouble(tick.ask - stopDistance, digits);
      tpPrice = NormalizeDouble(tick.ask + MathMax(upperBand - close1, stopDistance * PilotRewardRatio), digits);
      trigger = "H1 lower Bollinger touch plus RSI recovery; MACD=" + BoolLabel(macdBuyConfirm);
      reason = "BB_Triple H1 buy setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_BUY;
      return true;
   }
   if(bbSellSignal && rsiSellSignal && !macdSellConfirm)
   {
      score = sellScore;
      reason = "BB_Triple candidate tightened: sell requires MACD confirmation";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }
   if(bbSellSignal && rsiSellSignal)
   {
      direction = -1;
      score = 100.0;
      slPrice = NormalizeDouble(tick.bid + stopDistance, digits);
      tpPrice = NormalizeDouble(tick.bid - MathMax(close1 - lowerBand, stopDistance * PilotRewardRatio), digits);
      trigger = "H1 upper Bollinger touch plus RSI fade; MACD=" + BoolLabel(macdSellConfirm);
      reason = "BB_Triple H1 sell setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_SELL;
      return true;
   }

   score = MathMax(buyScore, sellScore);
   reason = ((buyScore >= sellScore) ? "BB H1 BUY bias " : "BB H1 SELL bias ") + FormatNumber(score, 0) + "/100";
   evalCode = PILOT_EVAL_NO_CROSS;
   return false;
}

bool DetectPilotBullishMacdDivergence(string symbol)
{
   double priceLow1 = 0.0, priceLow2 = 0.0, macdLow1 = 0.0, macdLow2 = 0.0;
   int pos1 = 0, pos2 = 0;
   for(int shift = 2; shift < PilotMacdLookback; shift++)
   {
      double lowPrev = iLow(symbol, PilotMacdTimeframe, shift + 1);
      double lowCurr = iLow(symbol, PilotMacdTimeframe, shift);
      double lowNext = iLow(symbol, PilotMacdTimeframe, shift - 1);
      if(lowCurr <= 0.0 || lowPrev <= 0.0 || lowNext <= 0.0)
         continue;
      if(lowCurr < lowPrev && lowCurr < lowNext)
      {
         if(pos1 == 0)
         {
            pos1 = shift;
            priceLow1 = lowCurr;
            macdLow1 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 0, shift);
         }
         else if(pos2 == 0)
         {
            pos2 = shift;
            priceLow2 = lowCurr;
            macdLow2 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 0, shift);
            break;
         }
      }
   }
   return (pos1 > 0 && pos2 > 0 && priceLow1 < priceLow2 && macdLow1 > macdLow2);
}

bool DetectPilotBearishMacdDivergence(string symbol)
{
   double priceHigh1 = 0.0, priceHigh2 = 0.0, macdHigh1 = 0.0, macdHigh2 = 0.0;
   int pos1 = 0, pos2 = 0;
   for(int shift = 2; shift < PilotMacdLookback; shift++)
   {
      double highPrev = iHigh(symbol, PilotMacdTimeframe, shift + 1);
      double highCurr = iHigh(symbol, PilotMacdTimeframe, shift);
      double highNext = iHigh(symbol, PilotMacdTimeframe, shift - 1);
      if(highCurr <= 0.0 || highPrev <= 0.0 || highNext <= 0.0)
         continue;
      if(highCurr > highPrev && highCurr > highNext)
      {
         if(pos1 == 0)
         {
            pos1 = shift;
            priceHigh1 = highCurr;
            macdHigh1 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 0, shift);
         }
         else if(pos2 == 0)
         {
            pos2 = shift;
            priceHigh2 = highCurr;
            macdHigh2 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 0, shift);
            break;
         }
      }
   }
   return (pos1 > 0 && pos2 > 0 && priceHigh1 > priceHigh2 && macdHigh1 < macdHigh2);
}

bool EvaluatePilotMacdH1Signal(string symbol, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode, string &trigger)
{
   direction = 0;
   score = 0.0;
   reason = "Waiting for MACD_Divergence H1 evaluation";
   trigger = "";
   slPrice = 0.0;
   tpPrice = 0.0;
   evalCode = PILOT_EVAL_NONE;

   MqlTick tick;
   ZeroMemory(tick);
   if(!CommonLegacyPilotPrecheck(symbol, PilotMacdTimeframe, MathMax(PilotMacdLookback + 5, 40), tick, reason, evalCode))
      return false;

   bool bullDiv = DetectPilotBullishMacdDivergence(symbol);
   bool bearDiv = DetectPilotBearishMacdDivergence(symbol);
   RegimeSnapshot regime = EvaluateRegimeAt(symbol, PilotMacdTimeframe, 0);
   if(bullDiv && IsDowntrendRegimeLabel(regime.label) && !bearDiv)
   {
      score = 100.0;
      reason = "MACD candidate tightened: bullish divergence skipped in downtrend regime";
      evalCode = PILOT_EVAL_RANGE_BLOCK;
      return false;
   }
   if(bearDiv && IsUptrendRegimeLabel(regime.label) && !bullDiv)
   {
      score = 100.0;
      reason = "MACD candidate tightened: bearish divergence skipped in uptrend regime";
      evalCode = PILOT_EVAL_RANGE_BLOCK;
      return false;
   }

   double atr1 = ATRValue(symbol, PilotMacdTimeframe, PilotATRPeriod, 1);
   double macdMain1 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 0, 1);
   double macdMain2 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 0, 2);
   double macdSignal1 = MACDValue(symbol, PilotMacdTimeframe, PilotMacdFast, PilotMacdSlow, PilotMacdSignal, 1, 1);
   if(atr1 <= 0.0)
   {
      reason = "MACD H1 ATR unavailable";
      evalCode = PILOT_EVAL_ATR_UNAVAILABLE;
      return false;
   }
   if(macdMain1 == EMPTY_VALUE || macdMain2 == EMPTY_VALUE || macdSignal1 == EMPTY_VALUE)
   {
      reason = "MACD H1 buffers not ready";
      evalCode = PILOT_EVAL_INDICATOR_NOT_READY;
      return false;
   }

   bool bullishMomentumConfirm = (macdMain1 > macdSignal1 && macdMain1 > macdMain2);
   bool bearishMomentumConfirm = (macdMain1 < macdSignal1 && macdMain1 < macdMain2);
   double stopDistance = atr1 * 2.0;
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(bullDiv && !bullishMomentumConfirm)
   {
      score = 70.0;
      reason = "MACD candidate tightened: bullish divergence requires current MACD momentum confirmation";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }
   if(bullDiv)
   {
      direction = 1;
      score = 100.0;
      slPrice = NormalizeDouble(tick.ask - stopDistance, digits);
      tpPrice = NormalizeDouble(tick.ask + stopDistance * 2.0, digits);
      trigger = "H1 bullish MACD divergence";
      reason = "MACD_Divergence H1 buy setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_BUY;
      return true;
   }
   if(bearDiv && !bearishMomentumConfirm)
   {
      score = 70.0;
      reason = "MACD candidate tightened: bearish divergence requires current MACD momentum confirmation";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }
   if(bearDiv)
   {
      direction = -1;
      score = 100.0;
      slPrice = NormalizeDouble(tick.bid + stopDistance, digits);
      tpPrice = NormalizeDouble(tick.bid - stopDistance * 2.0, digits);
      trigger = "H1 bearish MACD divergence";
      reason = "MACD_Divergence H1 sell setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_SELL;
      return true;
   }
   reason = "No MACD divergence found in the last " + IntegerToString(PilotMacdLookback) + " H1 bars";
   evalCode = PILOT_EVAL_NO_CROSS;
   return false;
}

bool EvaluatePilotSRM15Signal(string symbol, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode, string &trigger)
{
   direction = 0;
   score = 0.0;
   reason = "Waiting for SR_Breakout M15 evaluation";
   trigger = "";
   slPrice = 0.0;
   tpPrice = 0.0;
   evalCode = PILOT_EVAL_NONE;

   MqlTick tick;
   ZeroMemory(tick);
   if(!CommonLegacyPilotPrecheck(symbol, PilotSRTimeframe, MathMax(PilotSRLookback + 5, 30), tick, reason, evalCode))
      return false;

   double resistance = 0.0;
   double support = 999999.0;
   for(int shift = 1; shift <= PilotSRLookback; shift++)
   {
      double high = iHigh(symbol, PilotSRTimeframe, shift);
      double low = iLow(symbol, PilotSRTimeframe, shift);
      if(high > resistance)
         resistance = high;
      if(low > 0.0 && low < support)
         support = low;
   }
   double close1 = iClose(symbol, PilotSRTimeframe, 1);
   double close2 = iClose(symbol, PilotSRTimeframe, 2);
   double pip = PipSize(symbol);
   double atr1 = ATRValue(symbol, PilotSRTimeframe, PilotATRPeriod, 1);
   if(resistance <= 0.0 || support >= 999999.0 || close1 <= 0.0 || close2 <= 0.0 || pip <= 0.0 || atr1 <= 0.0)
   {
      reason = "SR M15 buffers not ready";
      evalCode = PILOT_EVAL_INDICATOR_NOT_READY;
      return false;
   }
   double avgVolume = 0.0;
   for(int v = 1; v <= 20; v++)
      avgVolume += (double)iVolume(symbol, PilotSRTimeframe, v);
   avgVolume /= 20.0;
   bool volumeConfirm = ((double)iVolume(symbol, PilotSRTimeframe, 1) > avgVolume * 1.05);
   double breakPrice = MathMax(0.0, PilotSRBreakPips) * pip;
   bool buyPrevBelow = (close2 < resistance);
   bool buyBreak = (close1 > resistance + breakPrice);
   bool sellPrevAbove = (close2 > support);
   bool sellBreak = (close1 < support - breakPrice);
   double buyScore = (double)((buyPrevBelow ? 1 : 0) + (buyBreak ? 1 : 0) + (volumeConfirm ? 1 : 0)) / 3.0 * 100.0;
   double sellScore = (double)((sellPrevAbove ? 1 : 0) + (sellBreak ? 1 : 0) + (volumeConfirm ? 1 : 0)) / 3.0 * 100.0;
   double stopDistance = atr1 * 1.5;
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(buyPrevBelow && buyBreak && !volumeConfirm)
   {
      score = buyScore;
      reason = "SR_Breakout candidate tightened: buy breakout requires volume confirmation";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }
   if(buyPrevBelow && buyBreak)
   {
      direction = 1;
      score = MathMax(80.0, buyScore);
      slPrice = NormalizeDouble(tick.ask - stopDistance, digits);
      tpPrice = NormalizeDouble(tick.ask + stopDistance * 2.0, digits);
      trigger = "M15 resistance breakout; volume=" + BoolLabel(volumeConfirm);
      reason = "SR_Breakout M15 buy setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_BUY;
      return true;
   }
   if(sellPrevAbove && sellBreak && !volumeConfirm)
   {
      score = sellScore;
      reason = "SR_Breakout candidate tightened: sell breakdown requires volume confirmation";
      evalCode = PILOT_EVAL_NO_CROSS;
      return false;
   }
   if(sellPrevAbove && sellBreak)
   {
      direction = -1;
      score = MathMax(80.0, sellScore);
      slPrice = NormalizeDouble(tick.bid + stopDistance, digits);
      tpPrice = NormalizeDouble(tick.bid - stopDistance * 2.0, digits);
      trigger = "M15 support breakdown; volume=" + BoolLabel(volumeConfirm);
      reason = "SR_Breakout M15 sell setup ported from MT4";
      evalCode = PILOT_EVAL_SIGNAL_SELL;
      return true;
   }
   score = MathMax(buyScore, sellScore);
   reason = ((buyScore >= sellScore) ? "SR M15 BUY bias " : "SR M15 SELL bias ") + FormatNumber(score, 0) + "/100";
   evalCode = PILOT_EVAL_NO_CROSS;
   return false;
}

bool EvaluateLegacyPilotRouteSignal(string strategyKey, string symbol, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode, string &trigger)
{
   if(strategyKey == "RSI_Reversal")
      return EvaluatePilotRsiH1Signal(symbol, direction, score, reason, slPrice, tpPrice, evalCode, trigger);
   if(strategyKey == "BB_Triple")
      return EvaluatePilotBBH1Signal(symbol, direction, score, reason, slPrice, tpPrice, evalCode, trigger);
   if(strategyKey == "MACD_Divergence")
      return EvaluatePilotMacdH1Signal(symbol, direction, score, reason, slPrice, tpPrice, evalCode, trigger);
   if(strategyKey == "SR_Breakout")
      return EvaluatePilotSRM15Signal(symbol, direction, score, reason, slPrice, tpPrice, evalCode, trigger);
   reason = "Unknown legacy pilot route";
   evalCode = PILOT_EVAL_NO_CROSS;
   return false;
}

bool ProcessLegacyPilotRoute(string strategyKey, string symbol, int symbolIndex, StrategyStatusSnapshot &states[], datetime &lastBarTimes[])
{
   if(symbolIndex < 0 || symbolIndex >= ArraySize(states))
      return false;

   bool candidateEnabled = IsLegacyPilotRouteCandidateEnabled(strategyKey);
   bool inScope = LegacyPilotRouteInScope(strategyKey, symbol);
   bool liveEnabled = IsLegacyPilotRouteLiveEnabled(strategyKey);
   states[symbolIndex].enabled = candidateEnabled && inScope;
   states[symbolIndex].active = false;
   states[symbolIndex].runtimeLabel = (candidateEnabled && inScope) ? (liveEnabled ? "ON" : "CAND") : "PORT";
   states[symbolIndex].adaptiveState = liveEnabled ? "CAUTION" : "CANDIDATE";
   states[symbolIndex].adaptiveReason = IsNonRsiLegacyPilotRoute(strategyKey)
      ? strategyKey + " route ported from MT4; live entry requires the strategy switch plus the non-RSI legacy authorization tag"
      : strategyKey + " route ported from MT4; live entry gated by strategy-specific live switch and shared pilot risk controls";
   states[symbolIndex].riskMultiplier = liveEnabled ? 1.0 : 0.0;

   if(!candidateEnabled || !inScope)
   {
      states[symbolIndex].status = "NO_DATA";
      states[symbolIndex].score = 0.0;
      states[symbolIndex].reason = inScope ? "Legacy route disabled" : "Route scope excludes this symbol";
      return false;
   }

   ENUM_TIMEFRAMES timeframe = LegacyPilotRouteTimeframe(strategyKey);
   if(!IsNewTrackedBar(symbol, timeframe, symbolIndex, lastBarTimes))
   {
      states[symbolIndex].active = true;
      states[symbolIndex].status = "WAIT_BAR";
      states[symbolIndex].score = 0.0;
      states[symbolIndex].reason = "Waiting for next " + TimeframeLabel(timeframe) + " bar";
      return false;
   }

   int direction = 0;
   double score = 0.0;
   string reason = "";
   string trigger = "";
   double slPrice = 0.0;
   double tpPrice = 0.0;
   int evalCode = PILOT_EVAL_NONE;
   bool hasSignal = EvaluateLegacyPilotRouteSignal(strategyKey, symbol, direction, score, reason, slPrice, tpPrice, evalCode, trigger);
   states[symbolIndex].active = true;
   states[symbolIndex].score = score;
   states[symbolIndex].reason = reason;
   if(!hasSignal || direction == 0)
   {
      states[symbolIndex].status = PilotEvalCodeLabel(evalCode);
      return false;
   }

   datetime eventBarTime = iTime(symbol, timeframe, 0);
   AppendShadowCandidateLedgerRowForTimeframe(symbol, timeframe, eventBarTime, LegacyPilotRouteName(strategyKey), direction, score, trigger,
      liveEnabled ? "Legacy MT4 route is live-enabled in this run; shared pilot risk controls still apply" :
                    "Legacy MT4 route candidate/backtest evidence only; live entries remain disabled pending validation");

   if(strategyKey == "RSI_Reversal" && direction < 0 && PilotRsiSellLiveBlocked && !MQLInfoInteger(MQL_TESTER))
   {
      states[symbolIndex].status = "LIVE_CANDIDATE";
      states[symbolIndex].reason = reason + " | RSI SELL live blocked; sell side demoted to shadow/candidate after live loss review";
      Print("QuantGod MT5 pilot order blocked: RSI SELL live side demoted to shadow/candidate strategy=", strategyKey,
            " symbol=", symbol,
            " reason=live_loss_review");
      return true;
   }

   if(!liveEnabled)
   {
      states[symbolIndex].status = "LIVE_CANDIDATE";
      states[symbolIndex].reason = reason + " | candidate-only; live switch is disabled";
      return false;
   }

   MqlTick tick;
   ZeroMemory(tick);
   SymbolInfoTick(symbol, tick);
   string newsReason = "";
   if(!PilotDirectionAllowedByNews(symbol, direction, tick, newsReason))
   {
      states[symbolIndex].status = "NEWS_FILTERED";
      states[symbolIndex].reason = newsReason;
      return true;
   }

   string startupReason = "";
   if(PilotStartupEntryGuardBlocks(symbol, startupReason))
   {
      states[symbolIndex].status = "STARTUP_GUARD";
      states[symbolIndex].reason = reason + " | " + startupReason;
      g_pilotTelemetry[symbolIndex].startupBlocks++;
      UpdatePilotTelemetrySnapshot(symbolIndex, states[symbolIndex].status, states[symbolIndex].reason, direction);
      Print("QuantGod MT5 pilot order blocked: startup entry guard strategy=", strategyKey,
            " symbol=", symbol, " reason=", startupReason);
      return true;
   }

   if(SendPilotMarketOrder(symbol, direction, slPrice, tpPrice, strategyKey))
   {
      states[symbolIndex].status = (direction > 0) ? "BUY_ORDER_SENT" : "SELL_ORDER_SENT";
      states[symbolIndex].reason = reason + " | " + strategyKey + " order sent with 0.01 lot";
   }
   else
   {
      states[symbolIndex].status = "ORDER_SEND_FAILED";
      states[symbolIndex].reason = reason + " | Order send failed, check MT5 Journal";
   }
   return true;
}

bool ShouldRetryRetcode(uint retcode)
{
   return retcode == TRADE_RETCODE_REQUOTE
       || retcode == TRADE_RETCODE_TIMEOUT
       || retcode == TRADE_RETCODE_CONNECTION
       || retcode == TRADE_RETCODE_PRICE_OFF;
}

void RegisterPilotOrderSendFailure(string symbol, int direction, uint retcode, string resultComment, bool retryExhausted)
{
   g_tradeRetryState.consecutiveFailures++;
   g_tradeRetryState.lastFailureAt = TimeCurrent();
   Print("QuantGod MT5 pilot order failed", (retryExhausted ? " after 3 retries" : " (permanent)"),
         ": symbol=", symbol,
         " dir=", direction,
         " retcode=", retcode,
         " comment=", resultComment,
         " consecutiveFailures=", g_tradeRetryState.consecutiveFailures);

   if(g_tradeRetryState.consecutiveFailures >= 3)
   {
      g_tradeRetryState.blockedUntil = TimeCurrent() + 5 * 60;
      Print("ALERT: Trade failed ", g_tradeRetryState.consecutiveFailures,
            " times in a row. Circuit breaker engaged until ",
            TimeToString(g_tradeRetryState.blockedUntil));
   }
}

bool SendPilotMarketOrder(string symbol, int direction, double slPrice, double tpPrice, string strategyKey)
{
   if(!IsPilotLiveMode())
   {
      Print("QuantGod MT5 pilot order blocked: live mode is disabled strategy=", strategyKey,
            " symbol=", symbol);
      return false;
   }
   if(strategyKey == "MA_Cross")
   {
      if(!EnablePilotMA)
      {
         Print("QuantGod MT5 pilot order blocked: MA_Cross live switch disabled symbol=", symbol);
         return false;
      }
   }
   else if(IsNonRsiLegacyPilotRoute(strategyKey) && !NonRsiLegacyLiveAuthorizationActive())
   {
      Print("QuantGod MT5 pilot order blocked: non-RSI legacy live authorization lock disabled strategy=", strategyKey,
            " symbol=", symbol, " state=", NonRsiLegacyLiveAuthorizationState(),
            " expectedTag=", NonRsiLegacyLiveAuthorizationExpectedTag());
      return false;
   }
   else if(!IsLegacyPilotRouteLiveEnabled(strategyKey))
   {
      Print("QuantGod MT5 pilot order blocked: legacy route live switch disabled strategy=", strategyKey,
            " symbol=", symbol);
      return false;
   }
   if(direction == 0)
      return false;

   string permissionBlocker = LiveTradePermissionBlocker(symbol);
   if(StringLen(permissionBlocker) > 0)
   {
      Print("QuantGod MT5 pilot order blocked: trade permission disabled strategy=", strategyKey,
            " symbol=", symbol,
            " blocker=", permissionBlocker,
            " accountTradeAllowed=", ((bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) ? "true" : "false"),
            " accountExpertTradeAllowed=", ((bool)AccountInfoInteger(ACCOUNT_TRADE_EXPERT) ? "true" : "false"),
            " symbolTradeMode=", SymbolTradeModeLabel(SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE)));
      return false;
   }

   double requestedVolume = PilotLotSize;
   if(strategyKey == "RSI_Reversal" && direction > 0)
      requestedVolume = AutonomousPatchEffectiveStageLotCap(requestedVolume);
   double volume = NormalizeVolumeForSymbol(symbol, requestedVolume);
   g_trade.SetExpertMagicNumber(PilotMagic);
   g_trade.SetDeviationInPoints(PilotDeviationPoints);
   g_trade.SetTypeFillingBySymbol(symbol);

   // Clamp SL to PilotMaxFloatingLossUSC (broker-side sentinel)
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize > 0 && tickValue > 0 && volume > 0 && slPrice > 0)
   {
      double entryPrice = (direction > 0) ? SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
      double maxLossPriceDist = (PilotMaxFloatingLossUSC / (volume * tickValue)) * tickSize;
      if(maxLossPriceDist > 0)
      {
         if(direction > 0)
         {
            double hardFloor = entryPrice - maxLossPriceDist;
            if(slPrice < hardFloor) slPrice = hardFloor;
         }
         else
         {
            double hardCeiling = entryPrice + maxLossPriceDist;
            if(slPrice > hardCeiling) slPrice = hardCeiling;
         }
      }
   }
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(slPrice > 0.0)
      slPrice = NormalizeDouble(slPrice, digits);
   if(tpPrice > 0.0)
      tpPrice = NormalizeDouble(tpPrice, digits);

   // Circuit breaker check
   if(TimeCurrent() < g_tradeRetryState.blockedUntil)
   {
      Print("QuantGod MT5 pilot order blocked: circuit breaker active until ",
            TimeToString(g_tradeRetryState.blockedUntil));
      return false;
   }

   string comment = PilotTradeComment(strategyKey, direction);
   for(int attempt = 0; attempt < 3; attempt++)
   {
      MqlTick sendTick;
      ZeroMemory(sendTick);
      SymbolInfoTick(symbol, sendTick);
      double expectedPrice = 0.0;
      if(direction > 0)
         expectedPrice = sendTick.ask;
      else if(direction < 0)
         expectedPrice = sendTick.bid;
      double spreadAtEntry = (sendTick.ask > 0.0 && sendTick.bid > 0.0) ? CalcSpreadPips(symbol, sendTick.bid, sendTick.ask) : 0.0;
      uint startedMs = GetTickCount();
      string intentId = "pilot-" + IntegerToString((long)CurrentServerTime()) + "-" + symbol + "-" + strategyKey + "-" + IntegerToString(direction) + "-" + IntegerToString(attempt + 1);
      bool ok = false;
      if(direction > 0)
         ok = g_trade.Buy(volume, symbol, 0.0, slPrice, tpPrice, comment);
      else if(direction < 0)
         ok = g_trade.Sell(volume, symbol, 0.0, slPrice, tpPrice, comment);

      uint retcode = g_trade.ResultRetcode();
      int latencyMs = (int)(GetTickCount() - startedMs);
      double fillPrice = g_trade.ResultPrice();
      if(fillPrice <= 0.0)
      {
         if(direction > 0)
            fillPrice = g_trade.ResultAsk();
         else if(direction < 0)
            fillPrice = g_trade.ResultBid();
      }
      if(ok && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED))
      {
         AppendPilotTradeResultFeedback(symbol, direction, strategyKey, intentId, attempt + 1, expectedPrice, fillPrice, spreadAtEntry, latencyMs, "ORDER_ACCEPTED");
         g_tradeRetryState.consecutiveFailures = 0;
         Print("QuantGod MT5 pilot order sent: strategy=", strategyKey,
               " symbol=", symbol,
               " dir=", direction > 0 ? "BUY" : "SELL",
               " volume=", DoubleToString(volume, 2),
               " sl=", DoubleToString(slPrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)),
               " tp=", DoubleToString(tpPrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)),
               " attempt=", attempt + 1);
         return true;
      }

      bool retryable = ShouldRetryRetcode(retcode);
      bool finalAttempt = (!retryable || attempt >= 2);
      AppendPilotTradeResultFeedback(symbol,
                                     direction,
                                     strategyKey,
                                     intentId,
                                     attempt + 1,
                                     expectedPrice,
                                     fillPrice,
                                     spreadAtEntry,
                                     latencyMs,
                                     (retryable && !finalAttempt) ? "ORDER_RETRY" : "ORDER_REJECTED");

      if(!retryable)
      {
         RegisterPilotOrderSendFailure(symbol, direction, retcode, g_trade.ResultComment(), false);
         return false;
      }

      if(!finalAttempt)
         Sleep(500 * (attempt + 1));
   }

   RegisterPilotOrderSendFailure(symbol, direction, g_trade.ResultRetcode(), g_trade.ResultComment(), true);
   return false;
}

void ClosePilotPositions(const string reason)
{
   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;

      g_trade.SetExpertMagicNumber(PilotMagic);
      g_trade.SetDeviationInPoints(PilotDeviationPoints);
      g_trade.SetTypeFillingBySymbol(PositionGetString(POSITION_SYMBOL));
      bool closed = g_trade.PositionClose(ticket);
      Print("QuantGod MT5 pilot emergency close ticket=", ticket,
            " ok=", (closed ? "true" : "false"),
            " retcode=", g_trade.ResultRetcode(),
            " reason=", reason);
   }
}

bool ModifyPilotPositionStops(ulong ticket, string symbol, double slPrice, double tpPrice)
{
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);

   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.symbol = symbol;
   request.sl = NormalizeDouble(slPrice, digits);
   request.tp = NormalizeDouble(tpPrice, digits);
   request.magic = PilotMagic;

   ResetLastError();
   bool ok = OrderSend(request, result);
   if(!ok || (result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED))
   {
      static datetime lastWarn = 0;
      datetime now = CurrentServerTime();
      if(now - lastWarn >= 60)
      {
         lastWarn = now;
         Print("QuantGod MT5 breakeven modify failed: ticket=", ticket,
               " symbol=", symbol,
               " retcode=", result.retcode,
               " err=", GetLastError(),
               " comment=", result.comment);
      }
      return false;
   }

   return true;
}

bool IsPilotRouteLiveEnabledByComment(string comment)
{
   string upper = ToUpperString(comment);
   if(StringFind(upper, "QG_RSI_REV") >= 0)
      return EnablePilotRsiH1Live;
   if(StringFind(upper, "QG_BB_TRIPLE") >= 0)
      return (EnablePilotBBH1Live && NonRsiLegacyLiveAuthorizationActive());
   if(StringFind(upper, "QG_MACD_DIV") >= 0)
      return (EnablePilotMacdH1Live && NonRsiLegacyLiveAuthorizationActive());
   if(StringFind(upper, "QG_SR_BREAK") >= 0)
      return (EnablePilotSRM15Live && NonRsiLegacyLiveAuthorizationActive());
   return true;
}

void ManageDemotedPilotRouteExits()
{
   if(!EnableDemotedPilotRouteExit)
      return;

   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;
      if(IsPilotRouteLiveEnabledByComment(comment))
         continue;

      double netProfit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      bool profitExit = (netProfit >= DemotedPilotRouteProfitExitUSC);
      bool maxLossExit = (DemotedPilotRouteMaxLossUSC > 0.0 &&
                          netProfit <= -MathAbs(DemotedPilotRouteMaxLossUSC));
      if(!profitExit && !maxLossExit)
         continue;

      g_trade.SetExpertMagicNumber(PilotMagic);
      g_trade.SetDeviationInPoints(PilotDeviationPoints);
      g_trade.SetTypeFillingBySymbol(symbol);
      bool closed = g_trade.PositionClose(ticket);
      Print("QuantGod MT5 demoted route exit ticket=", ticket,
            " symbol=", symbol,
            " net=", DoubleToString(netProfit, 2),
            " comment=", comment,
            " reason=", (profitExit ? "profit-or-breakeven" : "demoted-route-max-loss"),
            " ok=", (closed ? "true" : "false"),
            " retcode=", g_trade.ResultRetcode());
   }
}

void ManagePilotRsiTimeStops()
{
   if(!EnablePilotRsiTimeStopProtect)
      return;

   bool maxHoldOn = (PilotRsiMaxHoldMinutes > 0);
   bool dayChangeOn = PilotRsiCloseOnServerDayChange;
   if(!maxHoldOn && !dayChangeOn)
      return;

   datetime now = CurrentServerTime();
   int nowDayKey = ServerDayKeyFromTime(now);
   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;
      if(!IsPilotRsiPositionComment(comment))
         continue;

      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int ageMinutes = (int)MathMax(0, (long)(now - openTime) / 60);
      bool maxHoldTriggered = (maxHoldOn && ageMinutes >= MathMax(1, PilotRsiMaxHoldMinutes));
      bool serverDayChanged = (dayChangeOn &&
                               nowDayKey > 0 &&
                               ServerDayKeyFromTime(openTime) > 0 &&
                               ServerDayKeyFromTime(openTime) != nowDayKey);
      if(!maxHoldTriggered && !serverDayChanged)
         continue;

      double netProfit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      g_trade.SetExpertMagicNumber(PilotMagic);
      g_trade.SetDeviationInPoints(PilotDeviationPoints);
      g_trade.SetTypeFillingBySymbol(symbol);
      bool closed = g_trade.PositionClose(ticket);
      Print("QuantGod MT5 RSI time stop close ticket=", ticket,
            " symbol=", symbol,
            " age=", ageMinutes, "m",
            " net=", DoubleToString(netProfit, 2),
            " routeProtect=RSI_TIME_STOP",
            " trigger=", (serverDayChanged ? "server-day-change" : "max-hold"),
            " ok=", (closed ? "true" : "false"),
            " retcode=", g_trade.ResultRetcode());
   }
}

void ManagePilotRsiFailFastStops()
{
   if(!EnablePilotRsiFailFastProtect)
      return;

   bool pipsTriggerOn = (PilotRsiFailFastMinLossPips > 0.0);
   bool cashTriggerOn = (PilotRsiFailFastMaxLossUSC > 0.0);
   bool tightenOn = (PilotRsiFailFastStopBufferPips > 0.0 && (pipsTriggerOn || cashTriggerOn));
   bool closeOn = (PilotRsiFailFastCloseOnMaxLoss && cashTriggerOn);
   if(!tightenOn && !closeOn)
      return;

   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;
      if(!IsPilotRsiPositionComment(comment))
         continue;

      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int ageMinutes = (int)MathMax(0, (long)(CurrentServerTime() - openTime) / 60);
      if(ageMinutes < MathMax(0, PilotRsiFailFastMinAgeMinutes))
         continue;

      double pip = PipSize(symbol);
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(pip <= 0.0 || point <= 0.0)
         continue;

      MqlTick tick;
      ZeroMemory(tick);
      if(!SymbolInfoTick(symbol, tick) || tick.bid <= 0.0 || tick.ask <= 0.0)
         continue;

      long positionType = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      double netProfit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double adversePips = 0.0;
      if(positionType == POSITION_TYPE_BUY)
         adversePips = (openPrice - tick.bid) / pip;
      else if(positionType == POSITION_TYPE_SELL)
         adversePips = (tick.ask - openPrice) / pip;
      else
         continue;

      bool pipsTriggered = (pipsTriggerOn && adversePips >= MathAbs(PilotRsiFailFastMinLossPips));
      bool cashTriggered = (cashTriggerOn && netProfit <= -MathAbs(PilotRsiFailFastMaxLossUSC));
      if(!pipsTriggered && !cashTriggered)
         continue;

      if(closeOn && cashTriggered)
      {
         g_trade.SetExpertMagicNumber(PilotMagic);
         g_trade.SetDeviationInPoints(PilotDeviationPoints);
         g_trade.SetTypeFillingBySymbol(symbol);
         bool closed = g_trade.PositionClose(ticket);
         Print("QuantGod MT5 RSI failfast close ticket=", ticket,
               " symbol=", symbol,
               " age=", ageMinutes, "m",
               " adversePips=", DoubleToString(adversePips, 1),
               " net=", DoubleToString(netProfit, 2),
               " routeProtect=RSI_FAILFAST",
               " ok=", (closed ? "true" : "false"),
               " retcode=", g_trade.ResultRetcode());
         continue;
      }

      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      int stopsLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
      int freezeLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
      double minDistance = (double)MathMax(stopsLevel, freezeLevel) * point + point;
      double bufferDistance = MathMax(MathMax(0.1, PilotRsiFailFastStopBufferPips) * pip, minDistance);
      double stepDistance = MathMax(0.1, PilotRsiFailFastStepPips) * pip;
      double targetSL = 0.0;
      bool shouldModify = false;

      if(positionType == POSITION_TYPE_BUY)
      {
         targetSL = NormalizeDouble(tick.bid - bufferDistance, digits);
         if(currentSL > 0.0 && currentSL >= targetSL - stepDistance)
            continue;
         if(targetSL > tick.bid - minDistance)
            continue;
         shouldModify = true;
      }
      else if(positionType == POSITION_TYPE_SELL)
      {
         targetSL = NormalizeDouble(tick.ask + bufferDistance, digits);
         if(currentSL > 0.0 && currentSL <= targetSL + stepDistance)
            continue;
         if(targetSL < tick.ask + minDistance)
            continue;
         shouldModify = true;
      }

      if(shouldModify && ModifyPilotPositionStops(ticket, symbol, targetSL, currentTP))
      {
         Print("QuantGod MT5 RSI failfast stop tightened ticket=", ticket,
               " symbol=", symbol,
               " age=", ageMinutes, "m",
               " adversePips=", DoubleToString(adversePips, 1),
               " net=", DoubleToString(netProfit, 2),
               " routeProtect=RSI_FAILFAST",
               " newSL=", DoubleToString(targetSL, digits),
               " trigger=", (cashTriggered ? "cash" : "pips"));
      }
   }
}

void ManagePilotBreakevenStops()
{
   bool baseBreakevenOn = (EnablePilotBreakevenProtect && PilotBreakevenTriggerPips > 0.0);
   bool baseTrailingOn = (EnablePilotTrailingStop &&
                          PilotTrailingStartPips > 0.0 &&
                          PilotTrailingDistancePips > 0.0);
   bool rsiBreakevenOn = (EnablePilotRsiFastExitProtect && PilotRsiBreakevenTriggerPips > 0.0);
   bool rsiTrailingOn = (EnablePilotRsiFastExitProtect &&
                         PilotRsiTrailingStartPips > 0.0 &&
                         PilotRsiTrailingDistancePips > 0.0);
   if(!baseBreakevenOn && !baseTrailingOn && !rsiBreakevenOn && !rsiTrailingOn)
      return;

   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;

      bool isRsiPosition = IsPilotRsiPositionComment(comment);
      bool breakevenOn = isRsiPosition ? rsiBreakevenOn : baseBreakevenOn;
      bool trailingOn = isRsiPosition ? rsiTrailingOn : baseTrailingOn;
      if(!breakevenOn && !trailingOn)
         continue;

      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int ageMinutes = (int)MathMax(0, (long)(CurrentServerTime() - openTime) / 60);
      int minAgeMinutes = isRsiPosition ? MathMax(0, PilotRsiProtectMinAgeMinutes) : MathMax(0, PilotBreakevenMinAgeMinutes);
      if(ageMinutes < minAgeMinutes)
         continue;

      double pip = PipSize(symbol);
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(pip <= 0.0 || point <= 0.0)
         continue;

      MqlTick tick;
      ZeroMemory(tick);
      if(!SymbolInfoTick(symbol, tick) || tick.bid <= 0.0 || tick.ask <= 0.0)
         continue;

      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      long positionType = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      double breakevenTriggerPips = isRsiPosition ? MathMax(0.0, PilotRsiBreakevenTriggerPips) : MathMax(0.0, PilotBreakevenTriggerPips);
      double lockPips = isRsiPosition ? MathMax(0.0, PilotRsiBreakevenLockPips) : MathMax(0.0, PilotBreakevenLockPips);
      double trailingStartPips = isRsiPosition ? MathMax(0.0, PilotRsiTrailingStartPips) : MathMax(0.0, PilotTrailingStartPips);
      double trailingDistancePips = isRsiPosition ? MathMax(0.0, PilotRsiTrailingDistancePips) : MathMax(0.0, PilotTrailingDistancePips);
      double trailingStepPips = isRsiPosition ? MathMax(0.1, PilotRsiTrailingStepPips) : MathMax(0.1, PilotTrailingStepPips);
      double patchRiskPips = AutonomousPatchRiskPipsForPosition(symbol, positionType, openPrice, currentSL);
      double favorablePips = 0.0;
      double targetSL = 0.0;
      bool shouldModify = false;

      int stopsLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
      int freezeLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
      double minDistance = (double)MathMax(stopsLevel, freezeLevel) * point + point;
      double stepDistance = trailingStepPips * pip;

      if(positionType == POSITION_TYPE_BUY)
      {
         favorablePips = (tick.bid - openPrice) / pip;
         if(isRsiPosition && g_autonomousPatchRuntimeActive && patchRiskPips > 0.0)
         {
            if(g_autonomousPatchBreakevenDelayR > 0.0)
               breakevenTriggerPips = patchRiskPips * g_autonomousPatchBreakevenDelayR;
            if(g_autonomousPatchTrailStartR > 0.0)
               trailingStartPips = patchRiskPips * g_autonomousPatchTrailStartR;
            if(g_autonomousPatchMfeGivebackPct > 0.0 && favorablePips > 0.0)
               trailingDistancePips = MathMax(trailingStepPips, favorablePips * g_autonomousPatchMfeGivebackPct);
         }
         if(breakevenOn && favorablePips >= breakevenTriggerPips)
            targetSL = NormalizeDouble(openPrice + lockPips * pip, digits);
         if(trailingOn && favorablePips >= trailingStartPips)
         {
            double trailingSL = NormalizeDouble(tick.bid - trailingDistancePips * pip, digits);
            if(targetSL <= 0.0 || trailingSL > targetSL)
               targetSL = trailingSL;
         }
         if(targetSL <= 0.0)
            continue;

         if(currentSL > 0.0 && currentSL >= targetSL - stepDistance)
            continue;
         if(targetSL > tick.bid - minDistance)
            continue;
         shouldModify = true;
      }
      else if(positionType == POSITION_TYPE_SELL)
      {
         favorablePips = (openPrice - tick.ask) / pip;
         if(isRsiPosition && g_autonomousPatchRuntimeActive && patchRiskPips > 0.0)
         {
            if(g_autonomousPatchBreakevenDelayR > 0.0)
               breakevenTriggerPips = patchRiskPips * g_autonomousPatchBreakevenDelayR;
            if(g_autonomousPatchTrailStartR > 0.0)
               trailingStartPips = patchRiskPips * g_autonomousPatchTrailStartR;
            if(g_autonomousPatchMfeGivebackPct > 0.0 && favorablePips > 0.0)
               trailingDistancePips = MathMax(trailingStepPips, favorablePips * g_autonomousPatchMfeGivebackPct);
         }
         if(breakevenOn && favorablePips >= breakevenTriggerPips)
            targetSL = NormalizeDouble(openPrice - lockPips * pip, digits);
         if(trailingOn && favorablePips >= trailingStartPips)
         {
            double trailingSL = NormalizeDouble(tick.ask + trailingDistancePips * pip, digits);
            if(targetSL <= 0.0 || trailingSL < targetSL)
               targetSL = trailingSL;
         }
         if(targetSL <= 0.0)
            continue;

         if(currentSL > 0.0 && currentSL <= targetSL + stepDistance)
            continue;
         if(targetSL < tick.ask + minDistance)
            continue;
         shouldModify = true;
      }
      else
         continue;

      if(shouldModify && ModifyPilotPositionStops(ticket, symbol, targetSL, currentTP))
      {
         Print("QuantGod MT5 pilot stop protected ticket=", ticket,
               " symbol=", symbol,
               " age=", ageMinutes, "m",
               " favorablePips=", DoubleToString(favorablePips, 1),
               " routeProtect=", (isRsiPosition ? "RSI_FAST" : "BASE"),
               " newSL=", DoubleToString(targetSL, digits));
      }
   }
}

bool ManualSafetySymbolAllowed(string symbol)
{
   if(!ManualSafetyWatchlistOnly)
      return true;
   return (FindSymbolIndex(symbol) >= 0);
}

void ManageManualSafetyGuard()
{
   if(!EnableManualSafetyGuard)
      return;

   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      if(!ManualSafetySymbolAllowed(symbol))
         continue;

      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(IsPilotManagedPosition(comment, magic))
         continue;

      double netProfit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      if(ManualSafetyCloseOnMaxLoss &&
         ManualSafetyMaxLossUSC > 0.0 &&
         netProfit <= -MathAbs(ManualSafetyMaxLossUSC))
      {
         g_trade.SetDeviationInPoints(PilotDeviationPoints);
         g_trade.SetTypeFillingBySymbol(symbol);
         bool closed = g_trade.PositionClose(ticket);
         Print("QuantGod MT5 manual safety close ticket=", ticket,
               " symbol=", symbol,
               " net=", DoubleToString(netProfit, 2),
               " ok=", (closed ? "true" : "false"),
               " retcode=", g_trade.ResultRetcode());
         continue;
      }

      bool initialSlOn = (ManualSafetyInitialSLPips > 0.0);
      bool trailingOn = (EnableManualTrailingStop &&
                         ManualSafetyTrailingStartPips > 0.0 &&
                         ManualSafetyTrailingDistancePips > 0.0);
      if(!initialSlOn && !trailingOn)
         continue;

      double pip = PipSize(symbol);
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(pip <= 0.0 || point <= 0.0)
         continue;

      MqlTick tick;
      ZeroMemory(tick);
      if(!SymbolInfoTick(symbol, tick) || tick.bid <= 0.0 || tick.ask <= 0.0)
         continue;

      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      long positionType = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      double lockPips = MathMax(0.0, ManualSafetyBreakevenLockPips);
      double favorablePips = 0.0;
      double targetSL = 0.0;
      bool shouldModify = false;

      int stopsLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
      int freezeLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
      double minDistance = (double)MathMax(stopsLevel, freezeLevel) * point + point;
      double stepDistance = MathMax(0.1, ManualSafetyTrailingStepPips) * pip;

      if(positionType == POSITION_TYPE_BUY)
      {
         favorablePips = (tick.bid - openPrice) / pip;
         double fallbackSL = initialSlOn ? NormalizeDouble(openPrice - ManualSafetyInitialSLPips * pip, digits) : 0.0;
         if(ManualSafetyBreakevenTriggerPips > 0.0 &&
            favorablePips >= ManualSafetyBreakevenTriggerPips)
            targetSL = NormalizeDouble(openPrice + lockPips * pip, digits);
         if(trailingOn && favorablePips >= ManualSafetyTrailingStartPips)
         {
            double trailingSL = NormalizeDouble(tick.bid - ManualSafetyTrailingDistancePips * pip, digits);
            if(targetSL <= 0.0 || trailingSL > targetSL)
               targetSL = trailingSL;
         }
         if(targetSL <= 0.0 && initialSlOn && (currentSL <= 0.0 || currentSL < fallbackSL - point))
            targetSL = fallbackSL;
         if(targetSL <= 0.0)
            continue;

         if(currentSL > 0.0 && currentSL >= targetSL - stepDistance)
            continue;
         if(targetSL > tick.bid - minDistance)
            continue;
         shouldModify = true;
      }
      else if(positionType == POSITION_TYPE_SELL)
      {
         favorablePips = (openPrice - tick.ask) / pip;
         double fallbackSL = initialSlOn ? NormalizeDouble(openPrice + ManualSafetyInitialSLPips * pip, digits) : 0.0;
         if(ManualSafetyBreakevenTriggerPips > 0.0 &&
            favorablePips >= ManualSafetyBreakevenTriggerPips)
            targetSL = NormalizeDouble(openPrice - lockPips * pip, digits);
         if(trailingOn && favorablePips >= ManualSafetyTrailingStartPips)
         {
            double trailingSL = NormalizeDouble(tick.ask + ManualSafetyTrailingDistancePips * pip, digits);
            if(targetSL <= 0.0 || trailingSL < targetSL)
               targetSL = trailingSL;
         }
         if(targetSL <= 0.0 && initialSlOn && (currentSL <= 0.0 || currentSL > fallbackSL + point))
            targetSL = fallbackSL;
         if(targetSL <= 0.0)
            continue;

         if(currentSL > 0.0 && currentSL <= targetSL + stepDistance)
            continue;
         if(targetSL < tick.ask + minDistance)
            continue;
         shouldModify = true;
      }

      if(shouldModify && ModifyPilotPositionStops(ticket, symbol, targetSL, currentTP))
      {
         Print("QuantGod MT5 manual safety protected ticket=", ticket,
               " symbol=", symbol,
               " favorablePips=", DoubleToString(favorablePips, 1),
               " newSL=", DoubleToString(targetSL, digits));
      }
   }
}

void RunPilotExecutionLoop()
{
   ResetPilotRuntimeStates();
   EnsurePilotTelemetryState();
   if(!IsPilotLiveMode())
      return;
   UpdatePilotClosedStats();
   RefreshNewsFilterState();
   if(g_pilotRealizedLossToday >= PilotMaxRealizedLossDayUSC)
   {
      g_pilotKillSwitch = true;
      g_pilotKillReason = "Daily realized loss limit reached";
   }

   string consecutiveLossPauseReason = "";
   if(!g_pilotKillSwitch && PilotConsecutiveLossPauseActive(consecutiveLossPauseReason))
   {
      g_pilotKillSwitch = true;
      g_pilotKillReason = consecutiveLossPauseReason;
   }
   if(!g_pilotKillSwitch && SumPilotFloatingProfit() <= -MathAbs(PilotMaxFloatingLossUSC))
   {
      g_pilotKillSwitch = true;
      g_pilotKillReason = "Floating loss limit reached";
   }
   if(g_pilotKillSwitch && PilotCloseOnKillSwitch)
      ClosePilotPositions(g_pilotKillReason);
   ManageDemotedPilotRouteExits();
   ManageManualSafetyGuard();
   if(!g_pilotKillSwitch)
      ManagePilotRsiTimeStops();
   if(!g_pilotKillSwitch)
      ManagePilotRsiFailFastStops();
   if(!g_pilotKillSwitch)
      ManagePilotBreakevenStops();
   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      string symbol = g_symbols[i];
      g_maRuntimeStates[i].enabled = EnablePilotMA;
      g_maRuntimeStates[i].riskMultiplier = EnablePilotMA ? 1.0 : 0.0;
      g_maRuntimeStates[i].adaptiveState = g_pilotKillSwitch ? "COOLDOWN" : (EnablePilotMA ? "CAUTION" : "CANDIDATE");
      g_maRuntimeStates[i].adaptiveReason = g_pilotKillSwitch
         ? g_pilotKillReason
         : (EnablePilotMA
            ? "HFM MT5 0.01 live pilot with M15 trigger, H1 trend filter, range guard, post-loss cooldown, USDJPY news filter, hard SL/TP, and kill switch"
            : "MA_Cross live route is disabled while USDJPY RSI_Reversal is iterated after live loss review");
      if(g_pilotKillSwitch)
      {
         g_maRuntimeStates[i].active = false;
         g_maRuntimeStates[i].runtimeLabel = "PAUSED";
         g_maRuntimeStates[i].status = "AUTO_PAUSED";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = g_pilotKillReason;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, "AUTO_PAUSED", 0, 0.0, "KILL_SWITCH", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }
      if(CountPilotPositions() >= PilotMaxTotalPositions)
      {
         g_maRuntimeStates[i].active = false;
         g_maRuntimeStates[i].runtimeLabel = "LIMIT";
         g_maRuntimeStates[i].status = "PORTFOLIO_LIMIT";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = "Portfolio position limit reached";
         g_pilotTelemetry[i].portfolioBlocks++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, "PORTFOLIO_LIMIT", 0, 0.0, "PORTFOLIO_LIMIT", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }
      if(CountPilotPositions(symbol) >= PilotMaxPositionsPerSymbol)
      {
         g_maRuntimeStates[i].active = true;
         g_maRuntimeStates[i].runtimeLabel = "ON";
         g_maRuntimeStates[i].status = "IN_POSITION";
         g_maRuntimeStates[i].score = 100.0;
         g_maRuntimeStates[i].reason = "Pilot position already open on this symbol";
         g_pilotTelemetry[i].inPositionBlocks++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, "IN_POSITION", 0, 100.0, "PILOT_POSITION_LIMIT", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }
      if(PilotBlockManualPerSymbol && HasManualPositionOnSymbol(symbol))
      {
         g_maRuntimeStates[i].active = false;
         g_maRuntimeStates[i].runtimeLabel = "BLOCK";
         g_maRuntimeStates[i].status = "POSITION_LIMIT";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = "Manual position on symbol blocks pilot entries";
         g_pilotTelemetry[i].manualBlocks++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, "MANUAL_BLOCK", 0, 0.0, "MANUAL_POSITION", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }
      string cooldownReason = "";
      if(PilotLossCooldownActive(symbol, cooldownReason))
      {
         g_maRuntimeStates[i].active = false;
         g_maRuntimeStates[i].runtimeLabel = "COOL";
         g_maRuntimeStates[i].status = "LOSS_COOLDOWN";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = cooldownReason;
         g_pilotTelemetry[i].cooldownBlocks++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, "LOSS_COOLDOWN", 0, 0.0, "LOSS_COOLDOWN", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }
      string newsReason = "";
      if(PilotNewsBlocksSymbol(symbol, newsReason))
      {
         g_maRuntimeStates[i].active = false;
         g_maRuntimeStates[i].runtimeLabel = "NEWS";
         g_maRuntimeStates[i].status = "NEWS_BLOCK";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = newsReason;
         g_pilotTelemetry[i].newsBlocks++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, "NEWS_BLOCK", 0, 0.0, "NEWS_BLOCK", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }

      if(ProcessLegacyPilotRoute("RSI_Reversal", symbol, i, g_rsiRuntimeStates, g_lastRsiPilotBarTime))
         continue;
      if(ProcessLegacyPilotRoute("BB_Triple", symbol, i, g_bbRuntimeStates, g_lastBBPilotBarTime))
         continue;
      if(ProcessLegacyPilotRoute("MACD_Divergence", symbol, i, g_macdRuntimeStates, g_lastMacdPilotBarTime))
         continue;
      if(ProcessLegacyPilotRoute("SR_Breakout", symbol, i, g_srRuntimeStates, g_lastSRPilotBarTime))
         continue;

      if(!EnablePilotMA)
      {
         g_maRuntimeStates[i].active = false;
         g_maRuntimeStates[i].runtimeLabel = "OFF";
         g_maRuntimeStates[i].status = "ROUTE_DISABLED";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = "MA_Cross live route disabled by EnablePilotMA=false; legacy RSI/candidate routes continue independently";
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         continue;
      }

      if(!IsNewPilotBar(symbol, PilotSignalTimeframe, i))
      {
         g_maRuntimeStates[i].active = true;
         g_maRuntimeStates[i].runtimeLabel = "ON";
         g_maRuntimeStates[i].status = "WAIT_BAR";
         g_maRuntimeStates[i].score = 0.0;
         g_maRuntimeStates[i].reason = "Waiting for next M15 bar";
         if(g_newsState.biasActive)
            g_maRuntimeStates[i].reason += " | news " + PilotActionLabelForSymbol(symbol) +
               " after " + CurrentNewsEventLabel();
         g_pilotTelemetry[i].waitBarSkips++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         continue;
      }
      int direction = 0;
      double score = 0.0;
      string reason = "";
      double slPrice = 0.0;
      double tpPrice = 0.0;
      int evalCode = PILOT_EVAL_NONE;
      g_pilotTelemetry[i].evaluationPasses++;
      g_pilotTelemetry[i].lastEvalTime = TimeCurrent();
      AppendShadowCandidateRoutesForBar(symbol, i, iTime(symbol, PilotSignalTimeframe, 0));
      bool hasSignal = EvaluatePilotMASignal(symbol, i, direction, score, reason, slPrice, tpPrice, evalCode);
      string signalStatus = PilotEvalCodeLabel(evalCode);
      g_maRuntimeStates[i].active = true;
      g_maRuntimeStates[i].runtimeLabel = "ON";
      g_maRuntimeStates[i].score = score;
      g_maRuntimeStates[i].reason = reason;
      if(!hasSignal || direction == 0)
      {
         g_maRuntimeStates[i].status = "WAIT_SIGNAL";
         if(evalCode == PILOT_EVAL_SPREAD_BLOCK)
            g_pilotTelemetry[i].spreadBlocks++;
         else if(evalCode == PILOT_EVAL_SESSION_BLOCK)
            g_pilotTelemetry[i].sessionBlocks++;
         else if(evalCode == PILOT_EVAL_RANGE_BLOCK)
            g_pilotTelemetry[i].regimeBlocks++;
         else if(evalCode == PILOT_EVAL_NO_CROSS)
            g_pilotTelemetry[i].noCrossMisses++;
         if(g_newsState.biasActive)
            g_maRuntimeStates[i].reason = reason + " | news " + PilotActionLabelForSymbol(symbol) +
               " after " + CurrentNewsEventLabel();
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason);
         string blocker = (evalCode == PILOT_EVAL_SPREAD_BLOCK) ? "SPREAD" :
            (evalCode == PILOT_EVAL_SESSION_BLOCK) ? "SESSION" :
            (evalCode == PILOT_EVAL_RANGE_BLOCK) ? "RANGE_REGIME" :
            (evalCode == PILOT_EVAL_NOT_ENOUGH_BARS) ? "DATA_WARMUP" :
            (evalCode == PILOT_EVAL_TICK_UNAVAILABLE) ? "TICK_DATA" :
            (evalCode == PILOT_EVAL_INDICATOR_NOT_READY || evalCode == PILOT_EVAL_TREND_NOT_READY || evalCode == PILOT_EVAL_ATR_UNAVAILABLE) ? "INDICATOR_DATA" :
            "NO_SIGNAL";
         string action = (evalCode == PILOT_EVAL_RANGE_BLOCK || evalCode == PILOT_EVAL_SPREAD_BLOCK || evalCode == PILOT_EVAL_SESSION_BLOCK)
            ? "BLOCKED"
            : "OBSERVED";
         AppendShadowSignalLedgerForCurrentBar(symbol, i, signalStatus, direction, score, blocker, action, g_maRuntimeStates[i].reason);
         continue;
      }
      g_pilotTelemetry[i].signalHits++;
      g_pilotTelemetry[i].lastSignalTime = TimeCurrent();
      MqlTick tick;
      ZeroMemory(tick);
      SymbolInfoTick(symbol, tick);
      if(!PilotDirectionAllowedByNews(symbol, direction, tick, newsReason))
      {
         g_maRuntimeStates[i].status = "NEWS_FILTERED";
         g_maRuntimeStates[i].reason = newsReason;
         g_pilotTelemetry[i].newsFiltered++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason, direction);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, signalStatus, direction, score, "NEWS_DIRECTION_FILTER", "BLOCKED", g_maRuntimeStates[i].reason);
         continue;
      }
      string startupReason = "";
      if(PilotStartupEntryGuardBlocks(symbol, startupReason))
      {
         g_maRuntimeStates[i].status = "STARTUP_GUARD";
         g_maRuntimeStates[i].reason = reason + " | " + startupReason;
         g_pilotTelemetry[i].startupBlocks++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason, direction);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, signalStatus, direction, score, "STARTUP_GUARD", "BLOCKED", g_maRuntimeStates[i].reason);
         Print("QuantGod MT5 pilot order blocked: startup entry guard strategy=MA_Cross symbol=", symbol,
               " reason=", startupReason);
         continue;
      }
      if(SendPilotMarketOrder(symbol, direction, slPrice, tpPrice, "MA_Cross"))
      {
         g_maRuntimeStates[i].status = (direction > 0) ? "BUY_ORDER_SENT" : "SELL_ORDER_SENT";
         g_maRuntimeStates[i].reason = reason + " | Pilot order sent with 0.01 lot";
         g_pilotTelemetry[i].orderSent++;
         g_pilotTelemetry[i].lastOrderTime = TimeCurrent();
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason, direction);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, signalStatus, direction, score, "", "ORDER_SENT", g_maRuntimeStates[i].reason);
      }
      else
      {
         g_maRuntimeStates[i].status = "ORDER_SEND_FAILED";
         g_maRuntimeStates[i].reason = reason + " | Order send failed, check MT5 Journal";
         g_pilotTelemetry[i].orderFailed++;
         UpdatePilotTelemetrySnapshot(i, g_maRuntimeStates[i].status, g_maRuntimeStates[i].reason, direction);
         AppendShadowSignalLedgerForCurrentBar(symbol, i, signalStatus, direction, score, "ORDER_SEND_FAILED", "ORDER_FAILED", g_maRuntimeStates[i].reason);
      }
   }
}
string StrategyPlaceholderJson(string scopeSymbol, string statusReason)
{
   string json = "{";
   json += "\"enabled\": false, ";
   json += "\"active\": false, ";
   json += "\"scopeSymbol\": \"" + JsonEscape(scopeSymbol) + "\", ";
   json += "\"state\": \"WARMUP\", ";
   json += "\"riskMultiplier\": 0.00, ";
   json += "\"sampleTrades\": 0, ";
   json += "\"sampleWindowTrades\": 0, ";
   json += "\"winRate\": 0.0, ";
   json += "\"profitFactor\": 0.00, ";
   json += "\"avgNet\": 0.00, ";
   json += "\"netProfit\": 0.00, ";
   json += "\"disabledUntil\": \"\", ";
   json += "\"reason\": \"" + JsonEscape(statusReason) + "\", ";
   json += "\"positions\": 0, ";
   json += "\"portfolioPositions\": 0";
   json += "}";
   return json;
}

string SymbolStrategyPlaceholderJson(string statusReason)
{
   string json = "{";
   json += "\"status\": \"NO_DATA\", ";
   json += "\"score\": 0.0, ";
   json += "\"reason\": \"" + JsonEscape(statusReason) + "\", ";
   json += "\"adaptiveState\": \"WARMUP\", ";
   json += "\"adaptiveReason\": \"" + JsonEscape("MT5 phase 1 skeleton: execution engine not ported yet") + "\", ";
   json += "\"active\": false, ";
   json += "\"runtimeLabel\": \"PORT\", ";
   json += "\"riskMultiplier\": 0.00";
   json += "}";
   return json;
}

string DiagnosticPlaceholderJson(string statusReason)
{
   string json = "{";
   json += "\"status\": \"NO_DATA\", ";
   json += "\"score\": 0.0, ";
   json += "\"reason\": \"" + JsonEscape(statusReason) + "\"";
   json += "}";
   return json;
}

string UsdJpyShadowResearchStrategyJson(string strategyKey, string scopeSymbol)
{
   bool enabled = IsUsdJpyShadowResearchRouteEnabled(strategyKey) && IsUsdJpySymbol(scopeSymbol);
   string json = "{";
   json += "\"enabled\": " + JsonBool(enabled) + ", ";
   json += "\"active\": false, ";
   json += "\"scopeSymbol\": \"" + JsonEscape(scopeSymbol) + "\", ";
   json += "\"state\": \"" + JsonEscape(enabled ? "SHADOW_RESEARCH" : "DISABLED") + "\", ";
   json += "\"status\": \"" + JsonEscape(enabled ? "SHADOW_ONLY" : "DISABLED") + "\", ";
   json += "\"score\": 0.0, ";
   json += "\"riskMultiplier\": 0.00, ";
   json += "\"sampleTrades\": 0, ";
   json += "\"sampleWindowTrades\": 0, ";
   json += "\"winRate\": 0.0, ";
   json += "\"profitFactor\": 0.00, ";
   json += "\"avgNet\": 0.00, ";
   json += "\"netProfit\": 0.00, ";
   json += "\"disabledUntil\": \"\", ";
   json += "\"reason\": \"" + JsonEscape(enabled
      ? "USDJPY strategy factory shadow-only route: writes candidate evidence, never sends live orders"
      : "USDJPY strategy factory route disabled or outside USDJPY scope") + "\", ";
   json += "\"adaptiveState\": \"" + JsonEscape(enabled ? "CANDIDATE_ONLY" : "DISABLED") + "\", ";
   json += "\"adaptiveReason\": \"" + JsonEscape("Simulation first: ParamLab/backtest/governance/manual review required before any live promotion") + "\", ";
   json += "\"positions\": 0, ";
   json += "\"portfolioPositions\": " + IntegerToString(CountPilotPositions());
   json += "}";
   return json;
}

string BuildSymbolStrategyJson(string symbol, int symbolIndex, string strategyKey)
{
   if(strategyKey == "MA_Cross" && symbolIndex >= 0 && symbolIndex < ArraySize(g_maRuntimeStates) && (EnablePilotMA || IsPilotLiveMode()))
      return PilotStatusJson(g_maRuntimeStates[symbolIndex]);
   if(strategyKey == "RSI_Reversal" && symbolIndex >= 0 && symbolIndex < ArraySize(g_rsiRuntimeStates) && IsLegacyPilotRouteCandidateEnabled("RSI_Reversal"))
      return PilotStatusJson(g_rsiRuntimeStates[symbolIndex]);
   if(strategyKey == "BB_Triple" && symbolIndex >= 0 && symbolIndex < ArraySize(g_bbRuntimeStates) && IsLegacyPilotRouteCandidateEnabled("BB_Triple"))
      return PilotStatusJson(g_bbRuntimeStates[symbolIndex]);
   if(strategyKey == "MACD_Divergence" && symbolIndex >= 0 && symbolIndex < ArraySize(g_macdRuntimeStates) && IsLegacyPilotRouteCandidateEnabled("MACD_Divergence"))
      return PilotStatusJson(g_macdRuntimeStates[symbolIndex]);
   if(strategyKey == "SR_Breakout" && symbolIndex >= 0 && symbolIndex < ArraySize(g_srRuntimeStates) && IsLegacyPilotRouteCandidateEnabled("SR_Breakout"))
      return PilotStatusJson(g_srRuntimeStates[symbolIndex]);
   if(IsUsdJpyShadowResearchRoute(strategyKey))
      return UsdJpyShadowResearchStrategyJson(strategyKey, symbol);

   string placeholderReason = "MT5 phase 1 skeleton: JSON export is live, strategy execution port is not implemented yet";
   return SymbolStrategyPlaceholderJson(placeholderReason);
}

string BuildRootStrategyJson(string strategyKey)
{
   if(strategyKey == "MA_Cross" && (EnablePilotMA || IsPilotLiveMode()))
      return PilotAggregateJson(g_focusSymbol);
   if(strategyKey != "MA_Cross" && IsLegacyPilotRouteCandidateEnabled(strategyKey))
      return LegacyPilotAggregateJson(strategyKey, LegacyPilotAggregateScopeSymbol(strategyKey, g_focusSymbol));
   if(IsUsdJpyShadowResearchRoute(strategyKey))
      return UsdJpyShadowResearchStrategyJson(strategyKey, g_focusSymbol);

   string reason = "MT5 phase 1 skeleton: adaptive control and strategy execution have not been ported yet";
   return StrategyPlaceholderJson(g_focusSymbol, reason);
}

string BuildRootDiagnosticJson(string strategyKey)
{
   if(strategyKey == "MA_Cross" && ArraySize(g_maRuntimeStates) > 0 && (EnablePilotMA || IsPilotLiveMode()))
   {
      StrategyStatusSnapshot state = g_maRuntimeStates[0];
      string json = "{";
      json += "\"status\": \"" + JsonEscape(state.status) + "\", ";
      json += "\"score\": " + FormatNumber(state.score, 1) + ", ";
      json += "\"reason\": \"" + JsonEscape(state.reason) + "\"";
      json += "}";
      return json;
   }
   if(strategyKey == "RSI_Reversal" && ArraySize(g_rsiRuntimeStates) > 0 && IsLegacyPilotRouteCandidateEnabled("RSI_Reversal"))
      return PilotStatusJson(g_rsiRuntimeStates[0]);
   if(strategyKey == "BB_Triple" && ArraySize(g_bbRuntimeStates) > 0 && IsLegacyPilotRouteCandidateEnabled("BB_Triple"))
      return PilotStatusJson(g_bbRuntimeStates[0]);
   if(strategyKey == "MACD_Divergence" && ArraySize(g_macdRuntimeStates) > 0 && IsLegacyPilotRouteCandidateEnabled("MACD_Divergence"))
      return PilotStatusJson(g_macdRuntimeStates[0]);
   if(strategyKey == "SR_Breakout" && ArraySize(g_srRuntimeStates) > 0 && IsLegacyPilotRouteCandidateEnabled("SR_Breakout"))
      return PilotStatusJson(g_srRuntimeStates[0]);
   if(IsUsdJpyShadowResearchRoute(strategyKey))
      return UsdJpyShadowResearchStrategyJson(strategyKey, g_focusSymbol);

   string reason = "MT5 phase 1 skeleton: diagnostics become live after the MT5 strategy engine is ported";
   return DiagnosticPlaceholderJson(reason);
}

string DealEntryToPositionTypeString(long dealType)
{
   if(dealType == DEAL_TYPE_BUY)
      return "BUY";
   if(dealType == DEAL_TYPE_SELL)
      return "SELL";
   return "UNKNOWN";
}

string PositionTypeToString(long positionType)
{
   if(positionType == POSITION_TYPE_BUY)
      return "BUY";
   if(positionType == POSITION_TYPE_SELL)
      return "SELL";
   return "UNKNOWN";
}

string InferTradeSource(string comment)
{
   string upper = ToUpperString(comment);
   if(StringFind(upper, "QG_") >= 0 || StringFind(upper, "QUANTGOD") >= 0)
      return "EA";
   return "MANUAL";
}

string InferStrategyFromComment(string comment)
{
   if(StringFind(comment, "QG_MA_Cross") >= 0)
      return "MA_Cross";
   if(StringFind(comment, "QG_RSI_Rev") >= 0)
      return "RSI_Reversal";
   if(StringFind(comment, "QG_BB_Triple") >= 0)
      return "BB_Triple";
   if(StringFind(comment, "QG_MACD_Div") >= 0)
      return "MACD_Divergence";
   if(StringFind(comment, "QG_SR_Break") >= 0)
      return "SR_Breakout";
   if(InferTradeSource(comment) == "EA")
      return "QuantGod/Other";
   return "Manual/Other";
}

double PipSize(string symbol)
{
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(point <= 0.0)
      return 0.0;
   if(digits == 3 || digits == 5)
      return point * 10.0;
   return point;
}

string TimeframeLabel(ENUM_TIMEFRAMES timeframe)
{
   if(timeframe == PERIOD_M1) return "M1";
   if(timeframe == PERIOD_M5) return "M5";
   if(timeframe == PERIOD_M15) return "M15";
   if(timeframe == PERIOD_M30) return "M30";
   if(timeframe == PERIOD_H1) return "H1";
   if(timeframe == PERIOD_H4) return "H4";
   if(timeframe == PERIOD_D1) return "D1";
   return "UNKNOWN";
}

double ReadSingleBufferValue(int handle, int bufferIndex, int shift)
{
   if(handle == INVALID_HANDLE)
      return 0.0;

   double values[];
   ArraySetAsSeries(values, true);
   int copied = CopyBuffer(handle, bufferIndex, shift, 1, values);
   IndicatorRelease(handle);
   if(copied <= 0)
      return 0.0;
   return values[0];
}

double MAValue(string symbol, ENUM_TIMEFRAMES timeframe, int period, int shift, ENUM_MA_METHOD method)
{
   int handle = iMA(symbol, timeframe, period, 0, method, PRICE_CLOSE);
   return ReadSingleBufferValue(handle, 0, shift);
}

double ATRValue(string symbol, ENUM_TIMEFRAMES timeframe, int period, int shift)
{
   int handle = iATR(symbol, timeframe, period);
   return ReadSingleBufferValue(handle, 0, shift);
}

double ADXValue(string symbol, ENUM_TIMEFRAMES timeframe, int period, int shift)
{
   int handle = iADX(symbol, timeframe, period);
   return ReadSingleBufferValue(handle, 0, shift);
}

double RSIValue(string symbol, ENUM_TIMEFRAMES timeframe, int period, int shift)
{
   int handle = iRSI(symbol, timeframe, period, PRICE_CLOSE);
   return ReadSingleBufferValue(handle, 0, shift);
}

double BandsValue(string symbol, ENUM_TIMEFRAMES timeframe, int period, double deviation, int bufferIndex, int shift)
{
   int handle = iBands(symbol, timeframe, period, 0, deviation, PRICE_CLOSE);
   return ReadSingleBufferValue(handle, bufferIndex, shift);
}

double MACDValue(string symbol, ENUM_TIMEFRAMES timeframe, int fastPeriod, int slowPeriod, int signalPeriod, int bufferIndex, int shift)
{
   int handle = iMACD(symbol, timeframe, fastPeriod, slowPeriod, signalPeriod, PRICE_CLOSE);
   return ReadSingleBufferValue(handle, bufferIndex, shift);
}

RegimeSnapshot EvaluateRegimeAt(string symbol, ENUM_TIMEFRAMES timeframe, datetime eventTime)
{
   RegimeSnapshot snapshot;
   snapshot.label = "UNKNOWN";
   snapshot.timeframe = TimeframeLabel(timeframe);
   snapshot.directionalMovePips = 0.0;
   snapshot.averageRangePips = 0.0;
   snapshot.recentRangePips = 0.0;

   if(StringLen(symbol) == 0)
      return snapshot;

   datetime referenceTime = eventTime;
   if(referenceTime <= 0)
      referenceTime = TimeTradeServer();
   if(referenceTime <= 0)
      referenceTime = TimeCurrent();

   int shift = iBarShift(symbol, timeframe, referenceTime, false);
   if(shift < 0)
      return snapshot;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, timeframe, shift, 20, rates);
   if(copied < 8)
      return snapshot;

   double pipSize = PipSize(symbol);
   if(pipSize <= 0.0)
      return snapshot;

   int moveIndex = MathMin(5, copied - 1);
   double movePips = (rates[0].close - rates[moveIndex].close) / pipSize;

   int avgCount = MathMin(14, copied);
   double avgRangePips = 0.0;
   for(int i = 0; i < avgCount; i++)
      avgRangePips += (rates[i].high - rates[i].low) / pipSize;
   avgRangePips /= avgCount;

   int recentCount = MathMin(3, copied);
   double recentRangePips = 0.0;
   for(int i = 0; i < recentCount; i++)
      recentRangePips += (rates[i].high - rates[i].low) / pipSize;
   recentRangePips /= recentCount;

   snapshot.directionalMovePips = movePips;
   snapshot.averageRangePips = avgRangePips;
   snapshot.recentRangePips = recentRangePips;

   if(avgRangePips <= 0.0)
      return snapshot;

   double absMovePips = MathAbs(movePips);
   bool expanding = (recentRangePips >= avgRangePips * 1.20);
   bool tightening = (recentRangePips <= avgRangePips * 0.70);

   if(absMovePips >= avgRangePips * 1.10)
   {
      if(movePips > 0.0)
         snapshot.label = expanding ? "TREND_EXP_UP" : "TREND_UP";
      else
         snapshot.label = expanding ? "TREND_EXP_DOWN" : "TREND_DOWN";
   }
   else if(tightening)
   {
      snapshot.label = "RANGE_TIGHT";
   }
   else
   {
      snapshot.label = "RANGE";
   }

   return snapshot;
}

string CsvEscape(string value)
{
   string escaped = value;
   StringReplace(escaped, "\"", "\"\"");
   return "\"" + escaped + "\"";
}

bool IsExitDeal(long entryType)
{
   return (entryType == DEAL_ENTRY_OUT || entryType == DEAL_ENTRY_OUT_BY || entryType == DEAL_ENTRY_INOUT);
}

bool IsEntryDeal(long entryType)
{
   return (entryType == DEAL_ENTRY_IN || entryType == DEAL_ENTRY_INOUT);
}

bool FindPositionEntryDeal(ulong positionId, ulong &entryTicket)
{
   int total = HistoryDealsTotal();
   entryTicket = 0;

   for(int i = 0; i < total; i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      if((ulong)HistoryDealGetInteger(ticket, DEAL_POSITION_ID) != positionId)
         continue;
      long entryType = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      if(!IsEntryDeal(entryType))
         continue;
      entryTicket = ticket;
      return true;
   }

   return false;
}

int FindStrategyAggregateIndex(StrategyAggregateRecord &values[], string symbol, string strategy, string timeframe)
{
   for(int i = 0; i < ArraySize(values); i++)
   {
      if(values[i].symbol == symbol && values[i].strategy == strategy && values[i].timeframe == timeframe)
         return i;
   }
   return -1;
}

int FindRegimeAggregateIndex(RegimeAggregateRecord &values[], string symbol, string strategy, string timeframe, string entryRegime)
{
   for(int i = 0; i < ArraySize(values); i++)
   {
      if(values[i].symbol == symbol &&
         values[i].strategy == strategy &&
         values[i].timeframe == timeframe &&
         values[i].entryRegime == entryRegime)
         return i;
   }
   return -1;
}

void WriteTextFile(string fileName, string content)
{
   ResetLastError();
   int handle = FileOpen(fileName,
                         FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         0, CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("QuantGod MT5 skeleton failed to open file for write: ", fileName, " err=", GetLastError());
      return;
   }
   FileWriteString(handle, content);
   FileFlush(handle);
   FileClose(handle);
}

void AppendTextFile(string fileName, string content)
{
   ResetLastError();
   int handle = FileOpen(fileName,
                         FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         0, CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("QuantGod MT5 skeleton failed to open file for append: ", fileName, " err=", GetLastError());
      return;
   }
   FileSeek(handle, 0, SEEK_END);
   FileWriteString(handle, content);
   FileFlush(handle);
   FileClose(handle);
}

// Strategy JSON EA Contract Adapter BEGIN
string StrategyJsonContractReadAll(string fileName)
{
   ResetLastError();
   int handle = FileOpen(fileName,
                         FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         0, CP_UTF8);
   if(handle == INVALID_HANDLE)
      return "";

   string content = "";
   while(!FileIsEnding(handle))
   {
      string token = FileReadString(handle);
      if(StringLen(token) <= 0)
         continue;
      if(StringLen(content) > 0)
         content += "\n";
      content += token;
   }
   FileClose(handle);
   return content;
}

string StrategyJsonContractValue(string content, string key, string fallback = "")
{
   string lines[];
   int count = StringSplit(content, '\n', lines);
   string prefix = key + "=";
   for(int i = 0; i < count; i++)
   {
      string line = lines[i];
      StringReplace(line, "\r", "");
      if(StringFind(line, prefix) == 0)
         return StringSubstr(line, StringLen(prefix));
   }
   return fallback;
}

bool StrategyJsonContractBool(string content, string key, bool fallback = false)
{
   string value = StrategyJsonContractValue(content, key, fallback ? "true" : "false");
   if(value == "true" || value == "TRUE" || value == "1")
      return true;
   if(value == "false" || value == "FALSE" || value == "0")
      return false;
   return fallback;
}

double StrategyJsonContractDouble(string content, string key, double fallback = 0.0)
{
   string value = StrategyJsonContractValue(content, key, "");
   if(StringLen(value) <= 0)
      return fallback;
   double parsed = StringToDouble(value);
   if(!MathIsValidNumber(parsed))
      return fallback;
   return parsed;
}

int StrategyJsonContractInt(string content, string key, int fallback = 0)
{
   string value = StrategyJsonContractValue(content, key, "");
   if(StringLen(value) <= 0)
      return fallback;
   return (int)StringToInteger(value);
}

void AutonomousPatchAddRejectedField(string field, string &items)
{
   if(StringLen(items) > 0)
      items += ",";
   items += "\"" + JsonEscape(field) + "\"";
}

bool AutonomousPatchStageMayAffectLiveRuntime(string stage)
{
   return (stage == "MICRO_LIVE" || stage == "LIVE_LIMITED");
}

double AutonomousPatchClampDouble(double value, double minValue, double maxValue, double fallback)
{
   if(!MathIsValidNumber(value) || value <= 0.0)
      return fallback;
   return MathMax(minValue, MathMin(maxValue, value));
}

string RefreshAutonomousConfigPatchRuntimeAdapter()
{
   g_autonomousPatchLoaded = false;
   g_autonomousPatchRuntimeActive = false;
   g_autonomousPatchStatus = "WAITING_PATCH";
   g_autonomousPatchReasonZh = "等待 Agent 生成 Autonomous Config Patch。";
   g_autonomousPatchAppliedPatchId = "";
   g_autonomousPatchExecutionStage = "";
   g_autonomousPatchRejectedItems = "";
   g_autonomousPatchRsiBuyBand = 0.0;
   g_autonomousPatchRsiCrossbackThreshold = 0.0;
   g_autonomousPatchBreakevenDelayR = 0.0;
   g_autonomousPatchTrailStartR = 0.0;
   g_autonomousPatchMfeGivebackPct = 0.0;
   g_autonomousPatchStageMaxLot = 0.0;
   g_autonomousPatchMaxLot = 0.0;

   if(!EnableAutonomousConfigPatchRuntimeAdapter)
   {
      g_autonomousPatchStatus = "DISABLED";
      g_autonomousPatchReasonZh = "EA Autonomous Config Patch runtime adapter 已关闭。";
   }
   else
   {
      string content = StrategyJsonContractReadAll(AutonomousConfigPatchRuntimeFile);
      if(StringLen(content) > 0)
      {
         g_autonomousPatchLoaded = true;
         string schema = StrategyJsonContractValue(content, "schema", "");
         string symbol = StrategyJsonContractValue(content, "symbol", "");
         string strategy = StrategyJsonContractValue(content, "strategy", "");
         string direction = StrategyJsonContractValue(content, "direction", "");
         string stage = StrategyJsonContractValue(content, "executionStage", StrategyJsonContractValue(content, "stage", ""));
         bool patchWritable = StrategyJsonContractBool(content, "patchWritable", false);
         bool autoAppliedByAgent = StrategyJsonContractBool(content, "autoAppliedByAgent", false);
         bool requiresGovernance = StrategyJsonContractBool(content, "requiresAutonomousGovernance", false);
         bool liveMutationAllowed = StrategyJsonContractBool(content, "liveMutationAllowed", false);
         bool orderSendAllowed = StrategyJsonContractBool(content, "orderSendAllowed", false);
         bool presetMutationAllowed = StrategyJsonContractBool(content, "livePresetMutationAllowed", false);
         bool newsBypassAllowed = StrategyJsonContractBool(content, "newsHardBypassAllowed", false);
         bool runtimeBypassAllowed = StrategyJsonContractBool(content, "runtimeFreshnessBypassAllowed", false);
         bool fastlaneBypassAllowed = StrategyJsonContractBool(content, "fastlaneBypassAllowed", false);
         double maxLot = StrategyJsonContractDouble(content, "maxLot", 0.0);
         double stageMaxLot = StrategyJsonContractDouble(content, "stageMaxLot", 0.0);
         double rsiBuyBand = StrategyJsonContractDouble(content, "rsiBuyBand", 0.0);
         double rsiCrossbackThreshold = StrategyJsonContractDouble(content, "rsiCrossbackThreshold", 0.0);
         double breakevenDelayR = StrategyJsonContractDouble(content, "breakevenDelayR", 0.0);
         double trailStartR = StrategyJsonContractDouble(content, "trailStartR", 0.0);
         double mfeGivebackPct = StrategyJsonContractDouble(content, "mfeGivebackPct", 0.0);

         g_autonomousPatchAppliedPatchId = StrategyJsonContractValue(content, "patchId", "");
         g_autonomousPatchExecutionStage = stage;

         if(schema != "quantgod.autonomous_config_patch_ea.v1")
            AutonomousPatchAddRejectedField("schema", g_autonomousPatchRejectedItems);
         if(symbol != "USDJPYc")
            AutonomousPatchAddRejectedField("symbol", g_autonomousPatchRejectedItems);
         if(strategy != "RSI_Reversal")
            AutonomousPatchAddRejectedField("strategy", g_autonomousPatchRejectedItems);
         if(direction != "LONG")
            AutonomousPatchAddRejectedField("direction", g_autonomousPatchRejectedItems);
         bool stageMayAffectLive = AutonomousPatchStageMayAffectLiveRuntime(stage);
         if(stageMayAffectLive && !patchWritable)
            AutonomousPatchAddRejectedField("patchWritable", g_autonomousPatchRejectedItems);
         if(stageMayAffectLive && !autoAppliedByAgent)
            AutonomousPatchAddRejectedField("autoAppliedByAgent", g_autonomousPatchRejectedItems);
         if(!requiresGovernance)
            AutonomousPatchAddRejectedField("requiresAutonomousGovernance", g_autonomousPatchRejectedItems);
         if(liveMutationAllowed || orderSendAllowed || presetMutationAllowed)
            AutonomousPatchAddRejectedField("execution_permissions", g_autonomousPatchRejectedItems);
         if(newsBypassAllowed || runtimeBypassAllowed || fastlaneBypassAllowed)
            AutonomousPatchAddRejectedField("hard_gate_bypass", g_autonomousPatchRejectedItems);
         if(maxLot <= 0.0 || maxLot > 2.0)
            AutonomousPatchAddRejectedField("maxLot", g_autonomousPatchRejectedItems);
         if(stageMaxLot < 0.0 || stageMaxLot > 2.0)
            AutonomousPatchAddRejectedField("stageMaxLot", g_autonomousPatchRejectedItems);
         if(rsiBuyBand > 0.0 && (rsiBuyBand < 5.0 || rsiBuyBand > 45.0))
            AutonomousPatchAddRejectedField("rsiBuyBand", g_autonomousPatchRejectedItems);
         if(rsiCrossbackThreshold < 0.0 || rsiCrossbackThreshold > 20.0)
            AutonomousPatchAddRejectedField("rsiCrossbackThreshold", g_autonomousPatchRejectedItems);
         if(breakevenDelayR > 0.0 && (breakevenDelayR < 0.2 || breakevenDelayR > 3.0))
            AutonomousPatchAddRejectedField("breakevenDelayR", g_autonomousPatchRejectedItems);
         if(trailStartR > 0.0 && (trailStartR < 0.3 || trailStartR > 5.0))
            AutonomousPatchAddRejectedField("trailStartR", g_autonomousPatchRejectedItems);
         if(mfeGivebackPct > 0.0 && (mfeGivebackPct < 0.10 || mfeGivebackPct > 0.90))
            AutonomousPatchAddRejectedField("mfeGivebackPct", g_autonomousPatchRejectedItems);

         if(StringLen(g_autonomousPatchRejectedItems) > 0)
         {
            g_autonomousPatchStatus = "PATCH_REJECTED";
            g_autonomousPatchReasonZh = "Agent patch 含有越权或越界字段，EA 已拒绝运行时生效。";
         }
         else if(!stageMayAffectLive)
         {
            g_autonomousPatchStatus = "PATCH_OBSERVED_ONLY";
            g_autonomousPatchReasonZh = "Agent patch 已同步，但当前阶段不是 MICRO_LIVE/LIVE_LIMITED；EA 只记录，不改变实盘运行参数。";
         }
         else
         {
            g_autonomousPatchRuntimeActive = true;
            g_autonomousPatchStatus = "PATCH_ACTIVE";
            g_autonomousPatchReasonZh = "Agent patch 已通过白名单校验，EA 将仅对白名单 RSI/出场/阶段仓位上限参数生效。";
            g_autonomousPatchRsiBuyBand = AutonomousPatchClampDouble(rsiBuyBand, 5.0, 45.0, 0.0);
            g_autonomousPatchRsiCrossbackThreshold = MathMax(0.0, MathMin(20.0, rsiCrossbackThreshold));
            g_autonomousPatchBreakevenDelayR = AutonomousPatchClampDouble(breakevenDelayR, 0.2, 3.0, 0.0);
            g_autonomousPatchTrailStartR = AutonomousPatchClampDouble(trailStartR, 0.3, 5.0, 0.0);
            g_autonomousPatchMfeGivebackPct = AutonomousPatchClampDouble(mfeGivebackPct, 0.10, 0.90, 0.0);
            g_autonomousPatchStageMaxLot = MathMax(0.0, MathMin(2.0, stageMaxLot));
            g_autonomousPatchMaxLot = MathMax(0.0, MathMin(2.0, maxLot));
         }
      }
   }

   string json = "{";
   json += "\"schema\":\"quantgod.autonomous_config_patch_ea_status.v1\",";
   json += "\"updatedAt\":\"" + JsonEscape(FormatDateTime(TimeLocal(), true)) + "\",";
   json += "\"enabled\":" + JsonBool(EnableAutonomousConfigPatchRuntimeAdapter) + ",";
   json += "\"loaded\":" + JsonBool(g_autonomousPatchLoaded) + ",";
   json += "\"runtimeActive\":" + JsonBool(g_autonomousPatchRuntimeActive) + ",";
   json += "\"status\":\"" + JsonEscape(g_autonomousPatchStatus) + "\",";
   json += "\"reasonZh\":\"" + JsonEscape(g_autonomousPatchReasonZh) + "\",";
   json += "\"patchFile\":\"" + JsonEscape(AutonomousConfigPatchRuntimeFile) + "\",";
   json += "\"appliedPatchId\":\"" + JsonEscape(g_autonomousPatchAppliedPatchId) + "\",";
   json += "\"executionStage\":\"" + JsonEscape(g_autonomousPatchExecutionStage) + "\",";
   json += "\"rejectedFields\":[" + g_autonomousPatchRejectedItems + "],";
   json += "\"activeParameters\":{";
   json += "\"rsiBuyBand\":" + FormatNumber(g_autonomousPatchRsiBuyBand, 4) + ",";
   json += "\"rsiCrossbackThreshold\":" + FormatNumber(g_autonomousPatchRsiCrossbackThreshold, 4) + ",";
   json += "\"breakevenDelayR\":" + FormatNumber(g_autonomousPatchBreakevenDelayR, 4) + ",";
   json += "\"trailStartR\":" + FormatNumber(g_autonomousPatchTrailStartR, 4) + ",";
   json += "\"mfeGivebackPct\":" + FormatNumber(g_autonomousPatchMfeGivebackPct, 4) + ",";
   json += "\"stageMaxLot\":" + FormatNumber(g_autonomousPatchStageMaxLot, 2) + ",";
   json += "\"maxLot\":" + FormatNumber(g_autonomousPatchMaxLot, 2);
   json += "},";
   json += "\"safety\":{\"usdJpyOnly\":true,\"rsiLongOnly\":true,\"maxLotCap\":2.0,\"newsHardBypassAllowed\":false,\"runtimeFreshnessBypassAllowed\":false,\"fastlaneBypassAllowed\":false,\"orderSendAllowedByPatch\":false,\"livePresetMutationAllowed\":false}";
   json += "}";
   g_autonomousConfigPatchStatusJson = json;
   return json;
}

double AutonomousPatchEffectiveRsiBuyBand(double fallback)
{
   if(g_autonomousPatchRuntimeActive && g_autonomousPatchRsiBuyBand > 0.0)
      return g_autonomousPatchRsiBuyBand;
   return fallback;
}

double AutonomousPatchEffectiveRsiCrossbackThreshold(double fallback)
{
   if(g_autonomousPatchRuntimeActive)
      return g_autonomousPatchRsiCrossbackThreshold;
   return fallback;
}

double AutonomousPatchEffectiveStageLotCap(double fallback)
{
   if(g_autonomousPatchRuntimeActive && g_autonomousPatchStageMaxLot > 0.0)
      return MathMin(fallback, g_autonomousPatchStageMaxLot);
   return fallback;
}

double AutonomousPatchRiskPipsForPosition(string symbol, long positionType, double openPrice, double currentSL)
{
   double pip = PipSize(symbol);
   if(pip <= 0.0 || openPrice <= 0.0 || currentSL <= 0.0)
      return 0.0;
   if(positionType == POSITION_TYPE_BUY && currentSL < openPrice)
      return (openPrice - currentSL) / pip;
   if(positionType == POSITION_TYPE_SELL && currentSL > openPrice)
      return (currentSL - openPrice) / pip;
   return 0.0;
}

bool StrategyJsonContractModeAllowed(string mode)
{
   return (mode == "SHADOW_EVALUATION_ONLY" ||
           mode == "TESTER_EVALUATION_ONLY" ||
           mode == "PAPER_LIVE_SIM_EVALUATION_ONLY");
}

bool StrategyJsonGenericAdapterFamily(string strategyFamily)
{
   return (strategyFamily == "MA_Cross" ||
           strategyFamily == "BB_Triple" ||
           strategyFamily == "MACD_Divergence" ||
           strategyFamily == "SR_Breakout");
}

bool StrategyJsonEvaluateGenericAdapterFamily(string strategyFamily, string symbol, int symbolIndex, int &direction, double &score, string &reason, double &slPrice, double &tpPrice, int &evalCode, string &trigger)
{
   if(strategyFamily == "MA_Cross")
   {
      trigger = "";
      return EvaluatePilotMASignal(symbol, symbolIndex, direction, score, reason, slPrice, tpPrice, evalCode);
   }
   if(strategyFamily == "BB_Triple" ||
      strategyFamily == "MACD_Divergence" ||
      strategyFamily == "SR_Breakout")
      return EvaluateLegacyPilotRouteSignal(strategyFamily, symbol, direction, score, reason, slPrice, tpPrice, evalCode, trigger);

   direction = 0;
   score = 0.0;
   reason = "Strategy JSON generic adapter family is not implemented";
   slPrice = 0.0;
   tpPrice = 0.0;
   evalCode = PILOT_EVAL_NONE;
   trigger = "";
   return false;
}

string StrategyJsonGenericAdapterBlocker(string strategyFamily, int evalCode)
{
   string prefix = strategyFamily;
   StringReplace(prefix, "_", "");
   prefix = ToUpperString(prefix);
   if(evalCode == PILOT_EVAL_NOT_ENOUGH_BARS)
      return prefix + "_NOT_ENOUGH_BARS";
   if(evalCode == PILOT_EVAL_TICK_UNAVAILABLE)
      return "TICK_MISSING";
   if(evalCode == PILOT_EVAL_SPREAD_BLOCK)
      return "SPREAD_BLOCK";
   if(evalCode == PILOT_EVAL_SESSION_BLOCK)
      return "SESSION_CLOSED";
   if(evalCode == PILOT_EVAL_INDICATOR_NOT_READY)
      return prefix + "_INDICATORS_NOT_READY";
   if(evalCode == PILOT_EVAL_TREND_NOT_READY)
      return prefix + "_TREND_NOT_READY";
   if(evalCode == PILOT_EVAL_ATR_UNAVAILABLE)
      return prefix + "_ATR_NOT_READY";
   if(evalCode == PILOT_EVAL_RANGE_BLOCK)
      return prefix + "_REGIME_BLOCK";
   return prefix + "_SIGNAL_NOT_READY";
}

string StrategyJsonEAContractStatusFileName()
{
   return "QuantGod_StrategyJsonEAContractEAStatus.json";
}

string StrategyJsonEAShadowEvaluationStatusFileName()
{
   return "QuantGod_StrategyJsonEAShadowEvaluationStatus.json";
}

string StrategyJsonEAShadowEvaluationLedgerFileName()
{
   return "QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl";
}

ENUM_TIMEFRAMES StrategyJsonContractTimeframe(string label, ENUM_TIMEFRAMES fallback)
{
   string value = ToUpperString(label);
   if(value == "M1") return PERIOD_M1;
   if(value == "M5") return PERIOD_M5;
   if(value == "M15") return PERIOD_M15;
   if(value == "M30") return PERIOD_M30;
   if(value == "H1") return PERIOD_H1;
   if(value == "H4") return PERIOD_H4;
   if(value == "D1") return PERIOD_D1;
   return fallback;
}

int StrategyJsonUtcHourFromServerTime(datetime value)
{
   if(value <= 0)
      return -1;
   datetime serverNow = TimeCurrent();
   datetime gmtNow = TimeGMT();
   datetime utcValue = value - (serverNow - gmtNow);
   MqlDateTime dt;
   TimeToStruct(utcValue, dt);
   return dt.hour;
}

int StrategyJsonUtcDayKeyFromServerTime(datetime value)
{
   if(value <= 0)
      return 0;
   datetime serverNow = TimeCurrent();
   datetime gmtNow = TimeGMT();
   datetime utcValue = value - (serverNow - gmtNow);
   MqlDateTime dt;
   TimeToStruct(utcValue, dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
}

bool StrategyJsonHourInWindow(int hour, int startHour, int endHour)
{
   if(hour < 0)
      return false;
   int start = ((startHour % 24) + 24) % 24;
   int end = ((endHour % 24) + 24) % 24;
   if(start <= end)
      return (hour >= start && hour <= end);
   return (hour >= start || hour <= end);
}

string BuildStrategyJsonEAContractStatusJson()
{
   string content = "";
   bool loaded = false;
   string status = "WAITING_CONTRACT";
   string reason = "等待 Agent 生成 Strategy JSON EA 只读评估契约。";
   string selectedSeedId = "";
   string fingerprint = "";
   string contractMode = "";
   string focusSymbol = "";
   string strategyId = "";
   string strategyFamily = "";
   string direction = "";
   string lane = "";
   string entryMode = "";
   string rsiTimeframe = "";
   int rsiPeriod = 0;
   double rsiBuyBand = 0.0;
   double rsiCrossbackThreshold = 0.0;
   double breakevenDelayR = 0.0;
   double trailStartR = 0.0;
   double mfeGivebackPct = 0.0;
   double maxLot = 0.0;
   bool orderSendAllowed = false;
   bool livePresetMutationAllowed = false;
   bool gaDirectLiveAllowed = false;
   bool shadowOnly = true;
   bool wouldAffectLive = false;

   if(!EnableStrategyJsonEAContractAdapter)
   {
      status = "DISABLED";
      reason = "EA Strategy JSON 只读 adapter 已关闭。";
   }
   else
   {
      content = StrategyJsonContractReadAll(StrategyJsonEAContractFile);
      if(StringLen(content) > 0)
      {
         loaded = true;
         selectedSeedId = StrategyJsonContractValue(content, "selectedSeedId", "");
         fingerprint = StrategyJsonContractValue(content, "fingerprint", "");
         contractMode = StrategyJsonContractValue(content, "contractMode", "");
         focusSymbol = StrategyJsonContractValue(content, "focusSymbol", "");
         strategyId = StrategyJsonContractValue(content, "strategyId", "");
         strategyFamily = StrategyJsonContractValue(content, "strategyFamily", "");
         direction = StrategyJsonContractValue(content, "direction", "");
         lane = StrategyJsonContractValue(content, "lane", "");
         entryMode = StrategyJsonContractValue(content, "entryMode", "");
         rsiPeriod = StrategyJsonContractInt(content, "rsiPeriod", 0);
         rsiTimeframe = StrategyJsonContractValue(content, "rsiTimeframe", "");
         rsiBuyBand = StrategyJsonContractDouble(content, "rsiBuyBand", 0.0);
         rsiCrossbackThreshold = StrategyJsonContractDouble(content, "rsiCrossbackThreshold", 0.0);
         breakevenDelayR = StrategyJsonContractDouble(content, "breakevenDelayR", 0.0);
         trailStartR = StrategyJsonContractDouble(content, "trailStartR", 0.0);
         mfeGivebackPct = StrategyJsonContractDouble(content, "mfeGivebackPct", 0.0);
         maxLot = StrategyJsonContractDouble(content, "maxLot", 0.0);
         orderSendAllowed = StrategyJsonContractBool(content, "orderSendAllowed", false);
         livePresetMutationAllowed = StrategyJsonContractBool(content, "livePresetMutationAllowed", false);
         gaDirectLiveAllowed = StrategyJsonContractBool(content, "gaDirectLiveAllowed", false);
         shadowOnly = StrategyJsonContractBool(content, "shadowOnly", true);
         wouldAffectLive = StrategyJsonContractBool(content, "wouldAffectLive", false);

         if(orderSendAllowed || livePresetMutationAllowed || gaDirectLiveAllowed || wouldAffectLive)
         {
            status = "SAFETY_REJECTED";
            reason = "Strategy JSON contract 试图打开执行或 preset 权限，EA 已拒绝。";
         }
         else if(focusSymbol != "USDJPYc")
         {
            status = "SYMBOL_REJECTED";
            reason = "Strategy JSON contract 不是 USDJPYc，EA 已拒绝。";
         }
         else if(!StrategyJsonContractModeAllowed(contractMode))
         {
            status = "MODE_REJECTED";
            reason = "Strategy JSON contract 不是 shadow/tester/paper 只读评估模式。";
         }
         else
         {
            status = "SHADOW_CONTRACT_READY";
            reason = "EA 已加载 Strategy JSON 只读契约；仅用于 shadow/tester/paper lane 评估。";
         }
      }
   }

   bool liveEligible = (strategyFamily == "RSI_Reversal" && direction == "LONG" && focusSymbol == "USDJPYc");
   string json = "{";
   json += "\"schema\":\"quantgod.strategy_json_ea_contract_ea_status.v1\",";
   json += "\"updatedAt\":\"" + JsonEscape(FormatDateTime(TimeLocal(), true)) + "\",";
   json += "\"enabled\":" + JsonBool(EnableStrategyJsonEAContractAdapter) + ",";
   json += "\"loaded\":" + JsonBool(loaded) + ",";
   json += "\"status\":\"" + JsonEscape(status) + "\",";
   json += "\"reasonZh\":\"" + JsonEscape(reason) + "\",";
   json += "\"contractFile\":\"" + JsonEscape(StrategyJsonEAContractFile) + "\",";
   json += "\"selectedSeedId\":\"" + JsonEscape(selectedSeedId) + "\",";
   json += "\"fingerprint\":\"" + JsonEscape(fingerprint) + "\",";
   json += "\"contractMode\":\"" + JsonEscape(contractMode) + "\",";
   json += "\"focusSymbol\":\"" + JsonEscape(focusSymbol) + "\",";
   json += "\"strategyId\":\"" + JsonEscape(strategyId) + "\",";
   json += "\"strategyFamily\":\"" + JsonEscape(strategyFamily) + "\",";
   json += "\"direction\":\"" + JsonEscape(direction) + "\",";
   json += "\"lane\":\"" + JsonEscape(lane) + "\",";
   json += "\"entryMode\":\"" + JsonEscape(entryMode) + "\",";
   json += "\"rsiPeriod\":" + IntegerToString(rsiPeriod) + ",";
   json += "\"rsiTimeframe\":\"" + JsonEscape(rsiTimeframe) + "\",";
   json += "\"rsiBuyBand\":" + FormatNumber(rsiBuyBand, 4) + ",";
   json += "\"rsiCrossbackThreshold\":" + FormatNumber(rsiCrossbackThreshold, 4) + ",";
   json += "\"breakevenDelayR\":" + FormatNumber(breakevenDelayR, 4) + ",";
   json += "\"trailStartR\":" + FormatNumber(trailStartR, 4) + ",";
   json += "\"mfeGivebackPct\":" + FormatNumber(mfeGivebackPct, 4) + ",";
   json += "\"maxLot\":" + FormatNumber(maxLot, 2) + ",";
   json += "\"liveEligible\":" + JsonBool(liveEligible) + ",";
   json += "\"shadowOnly\":" + JsonBool(shadowOnly) + ",";
   json += "\"wouldAffectLive\":" + JsonBool(wouldAffectLive) + ",";
   json += "\"orderSendAllowed\":" + JsonBool(orderSendAllowed) + ",";
   json += "\"livePresetMutationAllowed\":" + JsonBool(livePresetMutationAllowed) + ",";
   json += "\"gaDirectLiveAllowed\":" + JsonBool(gaDirectLiveAllowed) + ",";
   json += "\"eaOwnsLiveExecution\":true";
   json += "}";
   return json;
}

string BuildStrategyJsonEAShadowEvaluationJson()
{
   string content = "";
   bool loaded = false;
   string status = "WAITING_CONTRACT";
   string blocker = "WAITING_CONTRACT";
   string reason = "等待 EA 读取 Strategy JSON 只读契约后生成 shadow evaluation。";
   string selectedSeedId = "";
   string fingerprint = "";
   string contractMode = "";
   string focusSymbol = "";
   string strategyId = "";
   string strategyFamily = "";
   string direction = "";
   string lane = "";
   string entryMode = "";
   string rsiTimeframeLabel = "";
   int rsiPeriod = 0;
   double rsiBuyBand = 0.0;
   double rsiCrossbackThreshold = 0.0;
   string maTimeframeLabel = "";
   int maFastPeriod = 9;
   int maSlowPeriod = 21;
   string bbTimeframeLabel = "";
   int bbPeriod = 20;
   double bbDeviations = 2.0;
   double bbReclaimBufferPips = 0.0;
   string macdTimeframeLabel = "";
   int macdFastPeriod = 12;
   int macdSlowPeriod = 26;
   int macdSignalPeriod = 9;
   double macdMinHistogramAbs = 0.0;
   string srTimeframeLabel = "";
   int srLookbackBars = 24;
   double srBreakoutBufferPips = 0.0;
   string tokyoTimeframeLabel = "";
   int tokyoRangeStartHourUtc = 0;
   int tokyoRangeEndHourUtc = 2;
   int tokyoTradeStartHourUtc = 3;
   int tokyoTradeEndHourUtc = 6;
   int tokyoLookbackBars = 8;
   double tokyoContractBufferPips = 0.0;
   string nightTimeframeLabel = "";
   int nightStartHourUtc = 20;
   int nightEndHourUtc = 2;
   int nightBollingerPeriod = 20;
   double nightDeviations = 1.8;
   double nightEntryBufferPips = 0.0;
   string h4TimeframeLabel = "";
   int h4FastEmaPeriod = 20;
   int h4SlowEmaPeriod = 50;
   int h4PullbackEmaPeriod = 20;
   int h4RsiPeriod = 14;
   double h4LongRsiMin = 38.0;
   double h4ShortRsiMax = 62.0;
   bool orderSendAllowed = false;
   bool livePresetMutationAllowed = false;
   bool gaDirectLiveAllowed = false;
   bool wouldAffectLive = false;

   if(!EnableStrategyJsonEAContractAdapter)
   {
      status = "DISABLED";
      blocker = "ADAPTER_DISABLED";
      reason = "EA Strategy JSON 只读 adapter 已关闭，无法生成 shadow evaluation。";
   }
   else
   {
      content = StrategyJsonContractReadAll(StrategyJsonEAContractFile);
      if(StringLen(content) > 0)
      {
         loaded = true;
         selectedSeedId = StrategyJsonContractValue(content, "selectedSeedId", "");
         fingerprint = StrategyJsonContractValue(content, "fingerprint", "");
         contractMode = StrategyJsonContractValue(content, "contractMode", "");
         focusSymbol = StrategyJsonContractValue(content, "focusSymbol", "");
         strategyId = StrategyJsonContractValue(content, "strategyId", "");
         strategyFamily = StrategyJsonContractValue(content, "strategyFamily", "");
         direction = StrategyJsonContractValue(content, "direction", "");
         lane = StrategyJsonContractValue(content, "lane", "");
         entryMode = StrategyJsonContractValue(content, "entryMode", "");
         rsiPeriod = StrategyJsonContractInt(content, "rsiPeriod", PilotRsiPeriod);
         rsiTimeframeLabel = StrategyJsonContractValue(content, "rsiTimeframe", TimeframeLabel(PilotRsiTimeframe));
         rsiBuyBand = StrategyJsonContractDouble(content, "rsiBuyBand", PilotRsiOversold);
         rsiCrossbackThreshold = StrategyJsonContractDouble(content, "rsiCrossbackThreshold", PilotRsiCrossbackThreshold);
         maTimeframeLabel = StrategyJsonContractValue(content, "maTimeframe", TimeframeLabel(PilotSignalTimeframe));
         maFastPeriod = StrategyJsonContractInt(content, "maFastPeriod", PilotFastMAPeriod);
         maSlowPeriod = StrategyJsonContractInt(content, "maSlowPeriod", PilotSlowMAPeriod);
         bbTimeframeLabel = StrategyJsonContractValue(content, "bbTimeframe", TimeframeLabel(PilotBBTimeframe));
         bbPeriod = StrategyJsonContractInt(content, "bbPeriod", PilotBBPeriod);
         bbDeviations = StrategyJsonContractDouble(content, "bbDeviations", PilotBBDeviation);
         bbReclaimBufferPips = StrategyJsonContractDouble(content, "bbReclaimBufferPips", 0.0);
         macdTimeframeLabel = StrategyJsonContractValue(content, "macdTimeframe", TimeframeLabel(PilotMacdTimeframe));
         macdFastPeriod = StrategyJsonContractInt(content, "macdFastPeriod", PilotMacdFast);
         macdSlowPeriod = StrategyJsonContractInt(content, "macdSlowPeriod", PilotMacdSlow);
         macdSignalPeriod = StrategyJsonContractInt(content, "macdSignalPeriod", PilotMacdSignal);
         macdMinHistogramAbs = StrategyJsonContractDouble(content, "macdMinHistogramAbs", 0.0);
         srTimeframeLabel = StrategyJsonContractValue(content, "srTimeframe", TimeframeLabel(PilotSRTimeframe));
         srLookbackBars = StrategyJsonContractInt(content, "srLookbackBars", PilotSRLookback);
         srBreakoutBufferPips = StrategyJsonContractDouble(content, "srBreakoutBufferPips", PilotSRBreakPips);
         tokyoTimeframeLabel = StrategyJsonContractValue(content, "tokyoTimeframe", "M15");
         tokyoRangeStartHourUtc = StrategyJsonContractInt(content, "tokyoRangeStartHourUtc", 0);
         tokyoRangeEndHourUtc = StrategyJsonContractInt(content, "tokyoRangeEndHourUtc", 2);
         tokyoTradeStartHourUtc = StrategyJsonContractInt(content, "tokyoTradeStartHourUtc", 3);
         tokyoTradeEndHourUtc = StrategyJsonContractInt(content, "tokyoTradeEndHourUtc", 6);
         tokyoLookbackBars = StrategyJsonContractInt(content, "tokyoLookbackBars", 8);
         tokyoContractBufferPips = StrategyJsonContractDouble(content, "tokyoBufferPips", 0.0);
         nightTimeframeLabel = StrategyJsonContractValue(content, "nightTimeframe", "M15");
         nightStartHourUtc = StrategyJsonContractInt(content, "nightStartHourUtc", 20);
         nightEndHourUtc = StrategyJsonContractInt(content, "nightEndHourUtc", 2);
         nightBollingerPeriod = StrategyJsonContractInt(content, "nightBollingerPeriod", 20);
         nightDeviations = StrategyJsonContractDouble(content, "nightDeviations", 1.8);
         nightEntryBufferPips = StrategyJsonContractDouble(content, "nightEntryBufferPips", 0.0);
         h4TimeframeLabel = StrategyJsonContractValue(content, "h4Timeframe", "H4");
         h4FastEmaPeriod = StrategyJsonContractInt(content, "h4FastEmaPeriod", 20);
         h4SlowEmaPeriod = StrategyJsonContractInt(content, "h4SlowEmaPeriod", 50);
         h4PullbackEmaPeriod = StrategyJsonContractInt(content, "h4PullbackEmaPeriod", 20);
         h4RsiPeriod = StrategyJsonContractInt(content, "h4RsiPeriod", 14);
         h4LongRsiMin = StrategyJsonContractDouble(content, "h4LongRsiMin", 38.0);
         h4ShortRsiMax = StrategyJsonContractDouble(content, "h4ShortRsiMax", 62.0);
         orderSendAllowed = StrategyJsonContractBool(content, "orderSendAllowed", false);
         livePresetMutationAllowed = StrategyJsonContractBool(content, "livePresetMutationAllowed", false);
         gaDirectLiveAllowed = StrategyJsonContractBool(content, "gaDirectLiveAllowed", false);
         wouldAffectLive = StrategyJsonContractBool(content, "wouldAffectLive", false);
      }
   }

   string symbol = g_focusSymbol;
   if(StringLen(focusSymbol) > 0)
      symbol = focusSymbol;
   if(StringLen(symbol) <= 0)
      symbol = "USDJPYc";

   MqlTick tick;
   ZeroMemory(tick);
   bool tickOk = SymbolInfoTick(symbol, tick);
   double bid = tickOk ? tick.bid : 0.0;
   double ask = tickOk ? tick.ask : 0.0;
   double spreadPips = tickOk ? CalcSpreadPips(symbol, bid, ask) : 0.0;
   bool spreadAllowed = (tickOk && spreadPips <= PilotMaxSpreadPips);
   bool sessionOpen = IsPilotSessionOpen();
   string newsReason = "";
   bool newsBlocked = PilotNewsBlocksSymbol(symbol, newsReason);

   ENUM_TIMEFRAMES rsiTimeframe = StrategyJsonContractTimeframe(rsiTimeframeLabel, PilotRsiTimeframe);
   int effectiveRsiPeriod = rsiPeriod > 0 ? rsiPeriod : PilotRsiPeriod;
   double effectiveBuyBand = rsiBuyBand > 0.0 ? rsiBuyBand : PilotRsiOversold;
   double effectiveThreshold = MathMax(0.0, rsiCrossbackThreshold);
   double rsi1 = RSIValue(symbol, rsiTimeframe, effectiveRsiPeriod, 1);
   double rsi2 = RSIValue(symbol, rsiTimeframe, effectiveRsiPeriod, 2);
   bool indicatorReady = (rsi1 > 0.0 && rsi2 > 0.0);
   bool rsiLongSignal = (indicatorReady && (rsi1 <= effectiveBuyBand || (rsi2 < effectiveBuyBand && rsi1 > effectiveBuyBand + effectiveThreshold)));
   bool hardGuardsPass = (tickOk && spreadAllowed && sessionOpen && !newsBlocked);
   bool wouldEnter = false;
   ENUM_TIMEFRAMES maTimeframe = StrategyJsonContractTimeframe(maTimeframeLabel, PilotSignalTimeframe);
   int effectiveMaFastPeriod = MathMax(2, maFastPeriod);
   int effectiveMaSlowPeriod = MathMax(effectiveMaFastPeriod + 1, maSlowPeriod);
   ENUM_TIMEFRAMES bbTimeframe = StrategyJsonContractTimeframe(bbTimeframeLabel, PilotBBTimeframe);
   int effectiveBbPeriod = MathMax(5, bbPeriod);
   double effectiveBbDeviations = MathMax(0.5, bbDeviations);
   double effectiveBbReclaimBufferPips = MathMax(0.0, bbReclaimBufferPips);
   ENUM_TIMEFRAMES macdTimeframe = StrategyJsonContractTimeframe(macdTimeframeLabel, PilotMacdTimeframe);
   int effectiveMacdFastPeriod = MathMax(2, macdFastPeriod);
   int effectiveMacdSlowPeriod = MathMax(effectiveMacdFastPeriod + 1, macdSlowPeriod);
   int effectiveMacdSignalPeriod = MathMax(2, macdSignalPeriod);
   double effectiveMacdMinHistogramAbs = MathMax(0.0, macdMinHistogramAbs);
   ENUM_TIMEFRAMES srTimeframe = StrategyJsonContractTimeframe(srTimeframeLabel, PilotSRTimeframe);
   int effectiveSrLookbackBars = MathMax(4, srLookbackBars);
   double effectiveSrBreakoutBufferPips = MathMax(0.0, srBreakoutBufferPips);
   ENUM_TIMEFRAMES contractTokyoTimeframe = StrategyJsonContractTimeframe(tokyoTimeframeLabel, PERIOD_M15);
   int effectiveTokyoRangeStartHourUtc = ((tokyoRangeStartHourUtc % 24) + 24) % 24;
   int effectiveTokyoRangeEndHourUtc = ((tokyoRangeEndHourUtc % 24) + 24) % 24;
   int effectiveTokyoTradeStartHourUtc = ((tokyoTradeStartHourUtc % 24) + 24) % 24;
   int effectiveTokyoTradeEndHourUtc = ((tokyoTradeEndHourUtc % 24) + 24) % 24;
   int effectiveTokyoLookbackBars = MathMax(2, tokyoLookbackBars);
   double effectiveTokyoBufferPips = MathMax(0.0, tokyoContractBufferPips);
   ENUM_TIMEFRAMES contractNightTimeframe = StrategyJsonContractTimeframe(nightTimeframeLabel, PERIOD_M15);
   int effectiveNightStartHourUtc = ((nightStartHourUtc % 24) + 24) % 24;
   int effectiveNightEndHourUtc = ((nightEndHourUtc % 24) + 24) % 24;
   int effectiveNightBollingerPeriod = MathMax(5, nightBollingerPeriod);
   double effectiveNightDeviations = MathMax(0.5, nightDeviations);
   double effectiveNightEntryBufferPips = MathMax(0.0, nightEntryBufferPips);
   ENUM_TIMEFRAMES h4TrendTimeframe = StrategyJsonContractTimeframe(h4TimeframeLabel, PERIOD_H4);
   int effectiveH4FastEmaPeriod = MathMax(2, h4FastEmaPeriod);
   int effectiveH4SlowEmaPeriod = MathMax(effectiveH4FastEmaPeriod + 1, h4SlowEmaPeriod);
   int effectiveH4PullbackEmaPeriod = MathMax(2, h4PullbackEmaPeriod);
   int effectiveH4RsiPeriod = MathMax(2, h4RsiPeriod);
   double effectiveH4LongRsiMin = MathMax(5.0, MathMin(95.0, h4LongRsiMin));
   double effectiveH4ShortRsiMax = MathMax(5.0, MathMin(95.0, h4ShortRsiMax));
   bool contractFamilyImplemented = (strategyFamily == "RSI_Reversal" ||
                                     StrategyJsonGenericAdapterFamily(strategyFamily) ||
                                     strategyFamily == "USDJPY_TOKYO_RANGE_BREAKOUT" ||
                                     strategyFamily == "USDJPY_NIGHT_REVERSION_SAFE" ||
                                     strategyFamily == "USDJPY_H4_TREND_PULLBACK");

   int genericDirection = 0;
   double genericScore = 0.0;
   string genericReason = "";
   string genericTrigger = "";
   double genericSL = 0.0;
   double genericTP = 0.0;
   int genericEvalCode = PILOT_EVAL_NONE;
   bool genericHasSignal = false;
   bool genericContractLong = (direction == "LONG");
   bool genericContractShort = (direction == "SHORT");
   bool genericDirectionSupported = (genericContractLong || genericContractShort);
   bool genericContractSignal = false;
   ENUM_TIMEFRAMES genericContractTimeframe = maTimeframe;
   if(StrategyJsonGenericAdapterFamily(strategyFamily))
   {
      ENUM_TIMEFRAMES genericTimeframe = maTimeframe;
      int genericMinBars = effectiveMaSlowPeriod + 5;
      if(strategyFamily == "BB_Triple")
      {
         genericTimeframe = bbTimeframe;
         genericMinBars = effectiveBbPeriod + 5;
      }
      else if(strategyFamily == "MACD_Divergence")
      {
         genericTimeframe = macdTimeframe;
         genericMinBars = effectiveMacdSlowPeriod + effectiveMacdSignalPeriod + 5;
      }
      else if(strategyFamily == "SR_Breakout")
      {
         genericTimeframe = srTimeframe;
         genericMinBars = effectiveSrLookbackBars + 5;
      }
      genericContractTimeframe = genericTimeframe;

      if(Bars(symbol, genericTimeframe) < genericMinBars)
      {
         genericReason = "Not enough bars for Strategy JSON " + strategyFamily + " contract parameters";
         genericEvalCode = PILOT_EVAL_NOT_ENOUGH_BARS;
      }
      else if(!tickOk)
      {
         genericReason = "Tick data unavailable";
         genericEvalCode = PILOT_EVAL_TICK_UNAVAILABLE;
      }
      else if(!spreadAllowed)
      {
         genericReason = "Spread above pilot limit";
         genericEvalCode = PILOT_EVAL_SPREAD_BLOCK;
      }
      else if(!sessionOpen)
      {
         genericReason = "Outside pilot trading session";
         genericEvalCode = PILOT_EVAL_SESSION_BLOCK;
      }
      else if(strategyFamily == "MA_Cross")
      {
         double fast1 = MAValue(symbol, maTimeframe, effectiveMaFastPeriod, 1, MODE_EMA);
         double fast2 = MAValue(symbol, maTimeframe, effectiveMaFastPeriod, 2, MODE_EMA);
         double slow1 = MAValue(symbol, maTimeframe, effectiveMaSlowPeriod, 1, MODE_EMA);
         double slow2 = MAValue(symbol, maTimeframe, effectiveMaSlowPeriod, 2, MODE_EMA);
         if(fast1 == EMPTY_VALUE || fast2 == EMPTY_VALUE || slow1 == EMPTY_VALUE || slow2 == EMPTY_VALUE)
         {
            genericReason = "MA contract buffers not ready";
            genericEvalCode = PILOT_EVAL_INDICATOR_NOT_READY;
         }
         else
         {
            bool maLongCross = (fast2 <= slow2 && fast1 > slow1);
            bool maShortCross = (fast2 >= slow2 && fast1 < slow1);
            if(maLongCross || maShortCross)
            {
               genericHasSignal = true;
               genericDirection = maLongCross ? 1 : -1;
               genericScore = 100.0;
               genericTrigger = "EMA_CROSS";
               genericReason = "Strategy JSON MA_Cross contract evaluated with fast/slow EMA parameters";
               genericEvalCode = maLongCross ? PILOT_EVAL_SIGNAL_BUY : PILOT_EVAL_SIGNAL_SELL;
            }
            else
            {
               genericReason = "Strategy JSON MA_Cross contract saw no EMA cross";
               genericEvalCode = PILOT_EVAL_NO_CROSS;
            }
         }
      }
      else if(strategyFamily == "BB_Triple")
      {
         double close1 = iClose(symbol, bbTimeframe, 1);
         double close2 = iClose(symbol, bbTimeframe, 2);
         double lower1 = BandsValue(symbol, bbTimeframe, effectiveBbPeriod, effectiveBbDeviations, 2, 1);
         double lower2 = BandsValue(symbol, bbTimeframe, effectiveBbPeriod, effectiveBbDeviations, 2, 2);
         double upper1 = BandsValue(symbol, bbTimeframe, effectiveBbPeriod, effectiveBbDeviations, 1, 1);
         double upper2 = BandsValue(symbol, bbTimeframe, effectiveBbPeriod, effectiveBbDeviations, 1, 2);
         double bbBuffer = effectiveBbReclaimBufferPips * PipSize(symbol);
         if(close1 <= 0.0 || close2 <= 0.0 || lower1 <= 0.0 || lower2 <= 0.0 || upper1 <= 0.0 || upper2 <= 0.0)
         {
            genericReason = "Bollinger contract buffers not ready";
            genericEvalCode = PILOT_EVAL_INDICATOR_NOT_READY;
         }
         else
         {
            bool bbLong = (close2 < lower2 && close1 > lower1 + bbBuffer);
            bool bbShort = (close2 > upper2 && close1 < upper1 - bbBuffer);
            if(bbLong || bbShort)
            {
               genericHasSignal = true;
               genericDirection = bbLong ? 1 : -1;
               genericScore = 100.0;
               genericTrigger = "BOLLINGER_RECLAIM";
               genericReason = "Strategy JSON BB_Triple contract evaluated with period/deviation/reclaim buffer";
               genericEvalCode = bbLong ? PILOT_EVAL_SIGNAL_BUY : PILOT_EVAL_SIGNAL_SELL;
            }
            else
            {
               genericReason = "Strategy JSON BB_Triple contract saw no Bollinger reclaim";
               genericEvalCode = PILOT_EVAL_NO_CROSS;
            }
         }
      }
      else if(strategyFamily == "MACD_Divergence")
      {
         double main1 = MACDValue(symbol, macdTimeframe, effectiveMacdFastPeriod, effectiveMacdSlowPeriod, effectiveMacdSignalPeriod, 0, 1);
         double signal1 = MACDValue(symbol, macdTimeframe, effectiveMacdFastPeriod, effectiveMacdSlowPeriod, effectiveMacdSignalPeriod, 1, 1);
         double main2 = MACDValue(symbol, macdTimeframe, effectiveMacdFastPeriod, effectiveMacdSlowPeriod, effectiveMacdSignalPeriod, 0, 2);
         double signal2 = MACDValue(symbol, macdTimeframe, effectiveMacdFastPeriod, effectiveMacdSlowPeriod, effectiveMacdSignalPeriod, 1, 2);
         if(main1 == EMPTY_VALUE || signal1 == EMPTY_VALUE || main2 == EMPTY_VALUE || signal2 == EMPTY_VALUE)
         {
            genericReason = "MACD contract buffers not ready";
            genericEvalCode = PILOT_EVAL_INDICATOR_NOT_READY;
         }
         else
         {
            double hist1 = main1 - signal1;
            double hist2 = main2 - signal2;
            bool macdLong = (hist2 <= 0.0 && hist1 > 0.0 && MathAbs(hist1) >= effectiveMacdMinHistogramAbs);
            bool macdShort = (hist2 >= 0.0 && hist1 < 0.0 && MathAbs(hist1) >= effectiveMacdMinHistogramAbs);
            if(macdLong || macdShort)
            {
               genericHasSignal = true;
               genericDirection = macdLong ? 1 : -1;
               genericScore = 100.0;
               genericTrigger = "MACD_HISTOGRAM_CROSS";
               genericReason = "Strategy JSON MACD_Divergence contract evaluated with MACD periods and histogram floor";
               genericEvalCode = macdLong ? PILOT_EVAL_SIGNAL_BUY : PILOT_EVAL_SIGNAL_SELL;
            }
            else
            {
               genericReason = "Strategy JSON MACD_Divergence contract saw no histogram cross";
               genericEvalCode = PILOT_EVAL_NO_CROSS;
            }
         }
      }
      else if(strategyFamily == "SR_Breakout")
      {
         double resistance = 0.0;
         double support = 999999.0;
         for(int shift = 2; shift <= effectiveSrLookbackBars + 1; shift++)
         {
            double high = iHigh(symbol, srTimeframe, shift);
            double low = iLow(symbol, srTimeframe, shift);
            if(high > resistance)
               resistance = high;
            if(low > 0.0 && low < support)
               support = low;
         }
         double close1 = iClose(symbol, srTimeframe, 1);
         double srBuffer = effectiveSrBreakoutBufferPips * PipSize(symbol);
         if(resistance <= 0.0 || support >= 999999.0 || close1 <= 0.0)
         {
            genericReason = "SR contract buffers not ready";
            genericEvalCode = PILOT_EVAL_INDICATOR_NOT_READY;
         }
         else
         {
            bool srLong = (close1 > resistance + srBuffer);
            bool srShort = (close1 < support - srBuffer);
            if(srLong || srShort)
            {
               genericHasSignal = true;
               genericDirection = srLong ? 1 : -1;
               genericScore = 100.0;
               genericTrigger = "SR_BREAKOUT";
               genericReason = "Strategy JSON SR_Breakout contract evaluated with lookback and buffer";
               genericEvalCode = srLong ? PILOT_EVAL_SIGNAL_BUY : PILOT_EVAL_SIGNAL_SELL;
            }
            else
            {
               genericReason = "Strategy JSON SR_Breakout contract saw no support/resistance breakout";
               genericEvalCode = PILOT_EVAL_NO_CROSS;
            }
         }
      }

      genericContractSignal = (genericHasSignal &&
                               ((genericContractLong && genericDirection > 0) ||
                                (genericContractShort && genericDirection < 0)));
   }

   ENUM_TIMEFRAMES tokyoTimeframe = contractTokyoTimeframe;
   datetime tokyoEventBarTime = iTime(symbol, tokyoTimeframe, 1);
   double tokyoOpen1 = iOpen(symbol, tokyoTimeframe, 1);
   double tokyoClose1 = iClose(symbol, tokyoTimeframe, 1);
   double tokyoAtr1 = ATRValue(symbol, tokyoTimeframe, PilotATRPeriod, 1);
   double tokyoPip = PipSize(symbol);
   int tokyoHourUtc = StrategyJsonUtcHourFromServerTime(tokyoEventBarTime);
   bool tokyoWindowActive = StrategyJsonHourInWindow(tokyoHourUtc, effectiveTokyoTradeStartHourUtc, effectiveTokyoTradeEndHourUtc);
   double tokyoBoxHigh = 0.0;
   double tokyoBoxLow = 0.0;
   int tokyoSamples = 0;
   if(tokyoEventBarTime > 0)
   {
      int tokyoDayKey = StrategyJsonUtcDayKeyFromServerTime(tokyoEventBarTime);
      int tokyoBars = Bars(symbol, tokyoTimeframe);
      int maxTokyoLookback = MathMin(tokyoBars - 1, effectiveTokyoLookbackBars);
      for(int shift = 1; shift <= maxTokyoLookback; shift++)
      {
         datetime barTime = iTime(symbol, tokyoTimeframe, shift);
         if(barTime <= 0)
            continue;
         if(StrategyJsonUtcDayKeyFromServerTime(barTime) != tokyoDayKey)
            continue;
         int barHourUtc = StrategyJsonUtcHourFromServerTime(barTime);
         if(!StrategyJsonHourInWindow(barHourUtc, effectiveTokyoRangeStartHourUtc, effectiveTokyoRangeEndHourUtc))
            continue;

         double high = iHigh(symbol, tokyoTimeframe, shift);
         double low = iLow(symbol, tokyoTimeframe, shift);
         if(high <= 0.0 || low <= 0.0)
            continue;
         if(tokyoSamples == 0)
         {
            tokyoBoxHigh = high;
            tokyoBoxLow = low;
         }
         else
         {
            tokyoBoxHigh = MathMax(tokyoBoxHigh, high);
            tokyoBoxLow = MathMin(tokyoBoxLow, low);
         }
         tokyoSamples++;
      }
   }
   double tokyoBoxPips = (tokyoPip > 0.0 && tokyoBoxHigh > tokyoBoxLow) ? (tokyoBoxHigh - tokyoBoxLow) / tokyoPip : 0.0;
   double tokyoBuffer = (tokyoPip > 0.0) ? effectiveTokyoBufferPips * tokyoPip : 0.0;
   double tokyoBufferPips = tokyoPip > 0.0 ? tokyoBuffer / tokyoPip : 0.0;
   double tokyoAdx = ADXValue(symbol, tokyoTimeframe, 14, 1);
   bool tokyoAdxPass = (tokyoAdx != EMPTY_VALUE && tokyoAdx >= 18.0);
   bool tokyoBoxReady = (tokyoSamples >= 2 && tokyoBoxHigh > tokyoBoxLow);
   bool tokyoIndicatorReady = (tokyoEventBarTime > 0 && tokyoClose1 > 0.0 && tokyoOpen1 > 0.0 && tokyoPip > 0.0 && tokyoBoxReady);
   bool tokyoBullishClose = (tokyoClose1 > tokyoOpen1);
   bool tokyoBearishClose = (tokyoClose1 < tokyoOpen1);
   bool tokyoBreakoutLong = (tokyoIndicatorReady && tokyoClose1 > tokyoBoxHigh + tokyoBuffer);
   bool tokyoBreakoutShort = (tokyoIndicatorReady && tokyoClose1 < tokyoBoxLow - tokyoBuffer);
   bool tokyoNearLong = (tokyoIndicatorReady && tokyoClose1 > tokyoBoxHigh - tokyoBuffer * 0.50 && tokyoBullishClose);
   bool tokyoNearShort = (tokyoIndicatorReady && tokyoClose1 < tokyoBoxLow + tokyoBuffer * 0.50 && tokyoBearishClose);
   bool tokyoOpportunityMode = (entryMode == "OPPORTUNITY_ENTRY");
   bool tokyoContractLong = (direction == "LONG");
   bool tokyoContractShort = (direction == "SHORT");
   bool tokyoLongSignal = tokyoBreakoutLong || (tokyoOpportunityMode && tokyoNearLong);
   bool tokyoShortSignal = tokyoBreakoutShort || (tokyoOpportunityMode && tokyoNearShort);
   bool tokyoContractSignal = ((tokyoContractLong && tokyoLongSignal) || (tokyoContractShort && tokyoShortSignal));
   int tokyoSignalDirection = tokyoContractSignal ? (tokyoContractLong ? 1 : -1) : 0;
   double tokyoScore = 0.0;
   if(tokyoContractLong && tokyoBreakoutLong)
      tokyoScore = 74.0;
   else if(tokyoContractShort && tokyoBreakoutShort)
      tokyoScore = 74.0;
   else if(tokyoContractLong && tokyoNearLong)
      tokyoScore = 52.0;
   else if(tokyoContractShort && tokyoNearShort)
      tokyoScore = 52.0;

   ENUM_TIMEFRAMES nightTimeframe = contractNightTimeframe;
   datetime nightEventBarTime = iTime(symbol, nightTimeframe, 1);
   double nightOpen1 = iOpen(symbol, nightTimeframe, 1);
   double nightClose1 = iClose(symbol, nightTimeframe, 1);
   double nightAtr1 = ATRValue(symbol, nightTimeframe, PilotATRPeriod, 1);
   double nightRsi1 = RSIValue(symbol, nightTimeframe, 14, 1);
   double nightUpperBand = BandsValue(symbol, nightTimeframe, effectiveNightBollingerPeriod, effectiveNightDeviations, 1, 1);
   double nightLowerBand = BandsValue(symbol, nightTimeframe, effectiveNightBollingerPeriod, effectiveNightDeviations, 2, 1);
   double nightAdx = ADXValue(symbol, nightTimeframe, 14, 1);
   int nightHourUtc = StrategyJsonUtcHourFromServerTime(nightEventBarTime);
   bool nightWindowActive = StrategyJsonHourInWindow(nightHourUtc, effectiveNightStartHourUtc, effectiveNightEndHourUtc);
   RegimeSnapshot nightRegime = EvaluateRegimeAt(symbol, PilotTrendTimeframe, nightEventBarTime);
   bool nightRangeRegime = (nightRegime.label == "RANGE" || nightRegime.label == "RANGE_TIGHT");
   bool nightAdxPass = (nightAdx != EMPTY_VALUE && nightAdx < 20.0);
   bool nightIndicatorReady = (nightEventBarTime > 0 &&
                               nightOpen1 > 0.0 &&
                               nightClose1 > 0.0 &&
                               nightUpperBand > 0.0 &&
                               nightLowerBand > 0.0 &&
                               nightUpperBand > nightLowerBand);
   bool nightBullishClose = (nightClose1 >= nightOpen1);
   bool nightBearishClose = (nightClose1 <= nightOpen1);
   double nightEntryBuffer = effectiveNightEntryBufferPips * PipSize(symbol);
   bool nightStrictLong = (nightIndicatorReady && nightClose1 <= nightLowerBand - nightEntryBuffer);
   bool nightStrictShort = (nightIndicatorReady && nightClose1 >= nightUpperBand + nightEntryBuffer);
   bool nightSoftLong = (nightIndicatorReady && nightClose1 <= nightLowerBand);
   bool nightSoftShort = (nightIndicatorReady && nightClose1 >= nightUpperBand);
   bool nightOpportunityMode = (entryMode == "OPPORTUNITY_ENTRY");
   bool nightContractLong = (direction == "LONG");
   bool nightContractShort = (direction == "SHORT");
   bool nightLongSignal = nightStrictLong || (nightOpportunityMode && nightSoftLong);
   bool nightShortSignal = nightStrictShort || (nightOpportunityMode && nightSoftShort);
   bool nightContractSignal = ((nightContractLong && nightLongSignal) || (nightContractShort && nightShortSignal));
   int nightSignalDirection = nightContractSignal ? (nightContractLong ? 1 : -1) : 0;
   double nightScore = 0.0;
   if(nightContractLong && nightStrictLong)
      nightScore = 64.0;
   else if(nightContractShort && nightStrictShort)
      nightScore = 64.0;
   else if(nightContractLong && nightSoftLong)
      nightScore = 50.0;
   else if(nightContractShort && nightSoftShort)
      nightScore = 50.0;

   ENUM_TIMEFRAMES h4SignalTimeframe = PERIOD_M15;
   datetime h4EventBarTime = iTime(symbol, h4SignalTimeframe, 1);
   double h4M15Open1 = iOpen(symbol, h4SignalTimeframe, 1);
   double h4M15Close1 = iClose(symbol, h4SignalTimeframe, 1);
   double h4M15High1 = iHigh(symbol, h4SignalTimeframe, 1);
   double h4M15Low1 = iLow(symbol, h4SignalTimeframe, 1);
   double h4M15Atr1 = ATRValue(symbol, h4SignalTimeframe, PilotATRPeriod, 1);
   double h4M15FastEma = MAValue(symbol, h4SignalTimeframe, effectiveH4FastEmaPeriod, 1, MODE_EMA);
   double h4M15SlowEma = MAValue(symbol, h4SignalTimeframe, effectiveH4PullbackEmaPeriod, 1, MODE_EMA);
   double h4Rsi1 = RSIValue(symbol, h4SignalTimeframe, effectiveH4RsiPeriod, 1);
   double h4Rsi2 = RSIValue(symbol, h4SignalTimeframe, effectiveH4RsiPeriod, 2);
   double h4Close1 = iClose(symbol, h4TrendTimeframe, 1);
   double h4Ema50 = MAValue(symbol, h4TrendTimeframe, effectiveH4FastEmaPeriod, 1, MODE_EMA);
   double h4Ema50Prev = MAValue(symbol, h4TrendTimeframe, effectiveH4FastEmaPeriod, 2, MODE_EMA);
   double h4Ema200 = MAValue(symbol, h4TrendTimeframe, effectiveH4SlowEmaPeriod, 1, MODE_EMA);
   bool h4HistoryReady = (Bars(symbol, h4TrendTimeframe) >= effectiveH4SlowEmaPeriod + 5);
   bool h4IndicatorReady = (h4HistoryReady &&
                            h4EventBarTime > 0 &&
                            h4M15Open1 > 0.0 &&
                            h4M15Close1 > 0.0 &&
                            h4M15High1 > 0.0 &&
                            h4M15Low1 > 0.0 &&
                            h4M15Atr1 > 0.0 &&
                            h4M15FastEma > 0.0 &&
                            h4M15SlowEma > 0.0 &&
                            h4Rsi1 > 0.0 &&
                            h4Close1 > 0.0 &&
                            h4Ema50 > 0.0 &&
                            h4Ema200 > 0.0);
   bool h4LongTrend = (h4IndicatorReady && h4Close1 > h4Ema200 && h4Ema50 > h4Ema200 && h4Ema50 >= h4Ema50Prev);
   bool h4ShortTrend = (h4IndicatorReady && h4Close1 < h4Ema200 && h4Ema50 < h4Ema200 && h4Ema50 <= h4Ema50Prev);
   bool h4BullishClose = (h4M15Close1 > h4M15Open1);
   bool h4BearishClose = (h4M15Close1 < h4M15Open1);
   bool h4LongPullback = (h4IndicatorReady &&
                          h4M15Low1 <= h4M15SlowEma &&
                          h4M15Close1 >= h4M15SlowEma &&
                          h4BullishClose &&
                          h4Rsi1 >= effectiveH4LongRsiMin);
   bool h4ShortPullback = (h4IndicatorReady &&
                           h4M15High1 >= h4M15SlowEma &&
                           h4M15Close1 <= h4M15SlowEma &&
                           h4BearishClose &&
                           h4Rsi1 <= effectiveH4ShortRsiMax);
   bool h4ContractLong = (direction == "LONG");
   bool h4ContractShort = (direction == "SHORT");
   bool h4ContractSignal = ((h4ContractLong && h4LongTrend && h4LongPullback) ||
                            (h4ContractShort && h4ShortTrend && h4ShortPullback));
   int h4SignalDirection = h4ContractSignal ? (h4ContractLong ? 1 : -1) : 0;
   double h4Score = h4ContractSignal ? 70.0 : 0.0;

   if(loaded)
   {
      if(orderSendAllowed || livePresetMutationAllowed || gaDirectLiveAllowed || wouldAffectLive)
      {
         status = "SAFETY_REJECTED";
         blocker = "CONTRACT_SAFETY_REJECTED";
         reason = "Strategy JSON contract 试图打开执行或 preset 权限，EA shadow evaluation 已拒绝。";
      }
      else if(focusSymbol != "USDJPYc")
      {
         status = "SYMBOL_REJECTED";
         blocker = "NON_USDJPY_CONTRACT";
         reason = "Strategy JSON contract 不是 USDJPYc，EA shadow evaluation 已拒绝。";
      }
      else if(!StrategyJsonContractModeAllowed(contractMode))
      {
         status = "MODE_REJECTED";
         blocker = "CONTRACT_MODE_REJECTED";
         reason = "Strategy JSON contract 不是 shadow/tester/paper 只读评估模式。";
      }
      else if(StrategyJsonGenericAdapterFamily(strategyFamily))
      {
         if(!genericDirectionSupported)
         {
            status = "DIRECTION_SHADOW_ONLY_DEMOTED";
            blocker = "EA_CONTRACT_DIRECTION_NOT_SUPPORTED";
            reason = strategyFamily + " contract 方向不是 LONG/SHORT，EA 只做 shadow 拒绝记录。";
         }
         else if(genericContractSignal)
         {
            status = "SHADOW_WOULD_ENTER";
            blocker = "NONE";
            reason = "EA 按 Strategy JSON contract 看到 " + strategyFamily + " shadow 机会；仅写入 shadow ledger，供 Case Memory/GA 使用。";
            wouldEnter = true;
         }
         else if(genericHasSignal)
         {
            status = "SHADOW_OBSERVE";
            blocker = "GENERIC_CONTRACT_OPPOSITE_DIRECTION_SIGNAL";
            reason = "EA 已读取 " + strategyFamily + " contract，但当前信号方向与 contract 方向不一致；继续 shadow 观察。";
         }
         else if(genericEvalCode == PILOT_EVAL_TICK_UNAVAILABLE ||
                 genericEvalCode == PILOT_EVAL_SPREAD_BLOCK ||
                 genericEvalCode == PILOT_EVAL_SESSION_BLOCK)
         {
            status = "SHADOW_GUARD_BLOCKED";
            blocker = StrategyJsonGenericAdapterBlocker(strategyFamily, genericEvalCode);
            reason = strategyFamily + " shadow evaluation 只记录机会；tick/spread/session 硬守门未通过，不会进入实盘。";
         }
         else if(genericEvalCode == PILOT_EVAL_NOT_ENOUGH_BARS ||
                 genericEvalCode == PILOT_EVAL_INDICATOR_NOT_READY ||
                 genericEvalCode == PILOT_EVAL_TREND_NOT_READY ||
                 genericEvalCode == PILOT_EVAL_ATR_UNAVAILABLE)
         {
            status = "SHADOW_WAIT_INDICATORS";
            blocker = StrategyJsonGenericAdapterBlocker(strategyFamily, genericEvalCode);
            reason = "EA 已读取 " + strategyFamily + " contract，等待对应 K 线/指标证据稳定。";
         }
         else if(genericEvalCode == PILOT_EVAL_RANGE_BLOCK)
         {
            status = "SHADOW_OBSERVE";
            blocker = StrategyJsonGenericAdapterBlocker(strategyFamily, genericEvalCode);
            reason = "EA 已读取 " + strategyFamily + " contract，但当前 regime/过滤器不适合该 legacy 路线；继续 shadow 观察。";
         }
         else
         {
            status = "SHADOW_OBSERVE";
            blocker = StrategyJsonGenericAdapterBlocker(strategyFamily, genericEvalCode);
            reason = "EA 已读取 " + strategyFamily + " contract；当前未触发 contract 方向的 legacy 策略条件。";
         }
      }
      else if(strategyFamily == "USDJPY_TOKYO_RANGE_BREAKOUT")
      {
         if(!EnableUsdJpyTokyoBreakoutShadowResearch)
         {
            status = "SHADOW_RESEARCH_ROUTE_DISABLED";
            blocker = "TOKYO_RANGE_ROUTE_DISABLED";
            reason = "USDJPY Tokyo Range Breakout 影子研究路线当前关闭；EA 不做 would-enter 评估。";
         }
         else if(!(tokyoContractLong || tokyoContractShort))
         {
            status = "DIRECTION_SHADOW_ONLY_DEMOTED";
            blocker = "EA_CONTRACT_DIRECTION_NOT_SUPPORTED";
            reason = "Tokyo Range Breakout contract 方向不是 LONG/SHORT，EA 只做 shadow 拒绝记录。";
         }
         else if(!tokyoIndicatorReady)
         {
            status = "SHADOW_WAIT_INDICATORS";
            if(!tokyoWindowActive)
               blocker = "TOKYO_RANGE_WAIT_WINDOW";
            else if(!tokyoBoxReady)
               blocker = "TOKYO_RANGE_BOX_NOT_READY";
            else
               blocker = "TOKYO_RANGE_INDICATORS_NOT_READY";
            reason = "EA 已读取 Tokyo Range Breakout contract，等待 JST 09-12 箱体、M15 bar、ATR/ADX 等影子评估证据稳定。";
         }
         else if(!tokyoWindowActive)
         {
            status = "SHADOW_OBSERVE";
            blocker = "TOKYO_RANGE_WAIT_BREAKOUT_WINDOW";
            reason = "Tokyo Range Breakout 只在 JST 12:00-18:00 观察箱体突破；当前继续 shadow 观察。";
         }
         else if(!hardGuardsPass)
         {
            status = "SHADOW_GUARD_BLOCKED";
            if(!tickOk)
               blocker = "TICK_MISSING";
            else if(!spreadAllowed)
               blocker = "SPREAD_BLOCK";
            else if(!sessionOpen)
               blocker = "SESSION_CLOSED";
            else if(newsBlocked)
               blocker = "NEWS_HARD_BLOCK";
            reason = "Tokyo Range Breakout shadow evaluation 只记录机会；runtime/session/spread/news 硬守门未通过，不会进入实盘。";
         }
         else if(tokyoContractSignal)
         {
            status = "SHADOW_WOULD_ENTER";
            blocker = "NONE";
            reason = "EA 按 Strategy JSON contract 看到 USDJPY Tokyo Range Breakout shadow 机会；仅写入 shadow ledger，供 Case Memory/GA 使用。";
            wouldEnter = true;
         }
         else
         {
            status = "SHADOW_OBSERVE";
            blocker = "TOKYO_RANGE_SIGNAL_NOT_READY";
            reason = "EA 已读取 Tokyo Range Breakout contract；当前未触发 contract 方向的箱体突破或机会入场条件。";
         }
      }
      else if(strategyFamily == "USDJPY_NIGHT_REVERSION_SAFE")
      {
         if(!EnableUsdJpyNightReversionShadowResearch)
         {
            status = "SHADOW_RESEARCH_ROUTE_DISABLED";
            blocker = "NIGHT_REVERSION_ROUTE_DISABLED";
            reason = "USDJPY Night Reversion 影子研究路线当前关闭；EA 不做 would-enter 评估。";
         }
         else if(!(nightContractLong || nightContractShort))
         {
            status = "DIRECTION_SHADOW_ONLY_DEMOTED";
            blocker = "EA_CONTRACT_DIRECTION_NOT_SUPPORTED";
            reason = "Night Reversion contract 方向不是 LONG/SHORT，EA 只做 shadow 拒绝记录。";
         }
         else if(!nightIndicatorReady)
         {
            status = "SHADOW_WAIT_INDICATORS";
            blocker = "NIGHT_REVERSION_INDICATORS_NOT_READY";
            reason = "EA 已读取 Night Reversion contract，等待 M15 bar、布林带、RSI、ATR/ADX 等影子评估证据稳定。";
         }
         else if(!nightWindowActive)
         {
            status = "SHADOW_OBSERVE";
            blocker = "NIGHT_REVERSION_WAIT_WINDOW";
            reason = "Night Reversion 只在 JST 21:00-08:30 低波动窗口观察均值回归；当前继续 shadow 观察。";
         }
         else if(!hardGuardsPass)
         {
            status = "SHADOW_GUARD_BLOCKED";
            if(!tickOk)
               blocker = "TICK_MISSING";
            else if(!spreadAllowed)
               blocker = "SPREAD_BLOCK";
            else if(!sessionOpen)
               blocker = "SESSION_CLOSED";
            else if(newsBlocked)
               blocker = "NEWS_HARD_BLOCK";
            reason = "Night Reversion shadow evaluation 只记录机会；runtime/session/spread/news 硬守门未通过，不会进入实盘。";
         }
         else if(nightContractSignal)
         {
            status = "SHADOW_WOULD_ENTER";
            blocker = "NONE";
            reason = "EA 按 Strategy JSON contract 看到 USDJPY Night Reversion shadow 机会；仅写入 shadow ledger，供 Case Memory/GA 使用。";
            wouldEnter = true;
         }
         else
         {
            status = "SHADOW_OBSERVE";
            blocker = "NIGHT_REVERSION_SIGNAL_NOT_READY";
            reason = "EA 已读取 Night Reversion contract；当前未触发 contract 方向的布林带/RSI 均值回归条件。";
         }
      }
      else if(strategyFamily == "USDJPY_H4_TREND_PULLBACK")
      {
         if(!EnableUsdJpyH4PullbackShadowResearch)
         {
            status = "SHADOW_RESEARCH_ROUTE_DISABLED";
            blocker = "H4_PULLBACK_ROUTE_DISABLED";
            reason = "USDJPY H4 Trend Pullback 影子研究路线当前关闭；EA 不做 would-enter 评估。";
         }
         else if(!(h4ContractLong || h4ContractShort))
         {
            status = "DIRECTION_SHADOW_ONLY_DEMOTED";
            blocker = "EA_CONTRACT_DIRECTION_NOT_SUPPORTED";
            reason = "H4 Trend Pullback contract 方向不是 LONG/SHORT，EA 只做 shadow 拒绝记录。";
         }
         else if(!h4IndicatorReady)
         {
            status = "SHADOW_WAIT_INDICATORS";
            blocker = "H4_PULLBACK_INDICATORS_NOT_READY";
            reason = "EA 已读取 H4 Trend Pullback contract，等待 H4 EMA50/200、M15 EMA/ATR/RSI 等影子评估证据稳定。";
         }
         else if((h4ContractLong && !h4LongTrend) || (h4ContractShort && !h4ShortTrend))
         {
            status = "SHADOW_OBSERVE";
            blocker = "H4_PULLBACK_TREND_NOT_READY";
            reason = "H4 Trend Pullback 要求 contract 方向与 H4 EMA50/200 趋势一致；当前大周期趋势未通过。";
         }
         else if(!hardGuardsPass)
         {
            status = "SHADOW_GUARD_BLOCKED";
            if(!tickOk)
               blocker = "TICK_MISSING";
            else if(!spreadAllowed)
               blocker = "SPREAD_BLOCK";
            else if(!sessionOpen)
               blocker = "SESSION_CLOSED";
            else if(newsBlocked)
               blocker = "NEWS_HARD_BLOCK";
            reason = "H4 Trend Pullback shadow evaluation 只记录机会；runtime/session/spread/news 硬守门未通过，不会进入实盘。";
         }
         else if(h4ContractSignal)
         {
            status = "SHADOW_WOULD_ENTER";
            blocker = "NONE";
            reason = "EA 按 Strategy JSON contract 看到 USDJPY H4 Trend Pullback shadow 机会；仅写入 shadow ledger，供 Case Memory/GA 使用。";
            wouldEnter = true;
         }
         else
         {
            status = "SHADOW_OBSERVE";
            blocker = "H4_PULLBACK_SIGNAL_NOT_READY";
            reason = "EA 已读取 H4 Trend Pullback contract；当前未触发 contract 方向的 M15 回踩恢复条件。";
         }
      }
      else if(strategyFamily != "RSI_Reversal")
      {
         status = "UNSUPPORTED_STRATEGY_FAMILY_SHADOW_OBSERVE";
         blocker = "EA_CONTRACT_FAMILY_NOT_IMPLEMENTED";
         reason = "EA 当前只对 RSI_Reversal、MA_Cross、BB_Triple、MACD_Divergence、SR_Breakout、USDJPY_TOKYO_RANGE_BREAKOUT、USDJPY_NIGHT_REVERSION_SAFE 与 USDJPY_H4_TREND_PULLBACK Strategy JSON contract 做逐 bar shadow evaluation；其他策略先进入 Case Memory/GA 待适配。";
      }
      else if(direction != "LONG")
      {
         status = "DIRECTION_SHADOW_ONLY_DEMOTED";
         blocker = "EA_CONTRACT_DIRECTION_NOT_LIVE_ROUTE";
         reason = "EA 已读取 Strategy JSON contract，但实盘首路线只允许 RSI_Reversal LONG；该方向只做 shadow 记录。";
      }
      else if(!indicatorReady)
      {
         status = "SHADOW_WAIT_INDICATORS";
         blocker = "INDICATORS_NOT_READY";
         reason = "EA 已读取 Strategy JSON contract，等待 RSI 指标稳定后继续 shadow evaluation。";
      }
      else if(!hardGuardsPass)
      {
         status = "SHADOW_GUARD_BLOCKED";
         if(!tickOk)
            blocker = "TICK_MISSING";
         else if(!spreadAllowed)
            blocker = "SPREAD_BLOCK";
         else if(!sessionOpen)
            blocker = "SESSION_CLOSED";
         else if(newsBlocked)
            blocker = "NEWS_HARD_BLOCK";
         reason = "Strategy JSON shadow evaluation 只记录机会；runtime/session/spread/news 硬守门未通过，不会进入实盘。";
      }
      else if(rsiLongSignal)
      {
         status = "SHADOW_WOULD_ENTER";
         blocker = "NONE";
         reason = "EA 按 Strategy JSON contract 看到 RSI LONG shadow 机会；仅写入 shadow ledger，供 Case Memory/GA 使用。";
         wouldEnter = true;
      }
      else
      {
         status = "SHADOW_OBSERVE";
         blocker = "RSI_CONTRACT_SIGNAL_NOT_READY";
         reason = "EA 已读取 Strategy JSON contract；当前 RSI LONG 条件未触发，继续 shadow 观察。";
      }
   }

   string evaluationId = selectedSeedId + "-" + fingerprint + "-" + IntegerToString((int)TimeLocal());
   string json = "{";
   json += "\"schema\":\"quantgod.strategy_json_ea_shadow_evaluation.v1\",";
   json += "\"evaluationId\":\"" + JsonEscape(evaluationId) + "\",";
   json += "\"generatedAtLocal\":\"" + JsonEscape(FormatDateTime(TimeLocal(), true)) + "\",";
   json += "\"generatedAtServer\":\"" + JsonEscape(FormatDateTime(CurrentServerTime(), true)) + "\",";
   json += "\"enabled\":" + JsonBool(EnableStrategyJsonEAContractAdapter) + ",";
   json += "\"loaded\":" + JsonBool(loaded) + ",";
   json += "\"status\":\"" + JsonEscape(status) + "\",";
   json += "\"blocker\":\"" + JsonEscape(blocker) + "\",";
   json += "\"reasonZh\":\"" + JsonEscape(reason) + "\",";
   json += "\"contractFile\":\"" + JsonEscape(StrategyJsonEAContractFile) + "\",";
   json += "\"selectedSeedId\":\"" + JsonEscape(selectedSeedId) + "\",";
   json += "\"fingerprint\":\"" + JsonEscape(fingerprint) + "\",";
   json += "\"contractMode\":\"" + JsonEscape(contractMode) + "\",";
   json += "\"strategyId\":\"" + JsonEscape(strategyId) + "\",";
   json += "\"strategyFamily\":\"" + JsonEscape(strategyFamily) + "\",";
   json += "\"direction\":\"" + JsonEscape(direction) + "\",";
   json += "\"lane\":\"" + JsonEscape(lane) + "\",";
   json += "\"entryMode\":\"" + JsonEscape(entryMode) + "\",";
   json += "\"symbol\":\"" + JsonEscape(symbol) + "\",";
   json += "\"timeframe\":\"" + JsonEscape(TimeframeLabel(rsiTimeframe)) + "\",";
   json += "\"contractFamilyImplemented\":" + JsonBool(contractFamilyImplemented) + ",";
   json += "\"rsiPeriod\":" + IntegerToString(effectiveRsiPeriod) + ",";
   json += "\"rsiClosed1\":" + FormatNumber(rsi1, 4) + ",";
   json += "\"rsiClosed2\":" + FormatNumber(rsi2, 4) + ",";
   json += "\"rsiBuyBand\":" + FormatNumber(effectiveBuyBand, 4) + ",";
   json += "\"rsiCrossbackThreshold\":" + FormatNumber(effectiveThreshold, 4) + ",";
   json += "\"indicatorReady\":" + JsonBool(indicatorReady) + ",";
   json += "\"rsiLongSignal\":" + JsonBool(rsiLongSignal) + ",";
   json += "\"wouldEnter\":" + JsonBool(wouldEnter) + ",";
   json += "\"hardGuardsPass\":" + JsonBool(hardGuardsPass) + ",";
   json += "\"sessionOpen\":" + JsonBool(sessionOpen) + ",";
   json += "\"spreadAllowed\":" + JsonBool(spreadAllowed) + ",";
   json += "\"spreadPips\":" + FormatNumber(spreadPips, 2) + ",";
   json += "\"maxSpreadPips\":" + FormatNumber(PilotMaxSpreadPips, 2) + ",";
   json += "\"newsBlocked\":" + JsonBool(newsBlocked) + ",";
   json += "\"newsReason\":\"" + JsonEscape(newsReason) + "\",";
   json += "\"contractParameters\":{";
   json += "\"ma\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(maTimeframe)) + "\",\"fastPeriod\":" + IntegerToString(effectiveMaFastPeriod) + ",\"slowPeriod\":" + IntegerToString(effectiveMaSlowPeriod) + "},";
   json += "\"bollinger\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(bbTimeframe)) + "\",\"period\":" + IntegerToString(effectiveBbPeriod) + ",\"deviations\":" + FormatNumber(effectiveBbDeviations, 4) + ",\"reclaimBufferPips\":" + FormatNumber(effectiveBbReclaimBufferPips, 2) + "},";
   json += "\"macd\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(macdTimeframe)) + "\",\"fastPeriod\":" + IntegerToString(effectiveMacdFastPeriod) + ",\"slowPeriod\":" + IntegerToString(effectiveMacdSlowPeriod) + ",\"signalPeriod\":" + IntegerToString(effectiveMacdSignalPeriod) + ",\"minHistogramAbs\":" + FormatNumber(effectiveMacdMinHistogramAbs, 6) + "},";
   json += "\"supportResistance\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(srTimeframe)) + "\",\"lookbackBars\":" + IntegerToString(effectiveSrLookbackBars) + ",\"breakoutBufferPips\":" + FormatNumber(effectiveSrBreakoutBufferPips, 2) + "},";
   json += "\"tokyoRange\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(tokyoTimeframe)) + "\",\"rangeStartHourUtc\":" + IntegerToString(effectiveTokyoRangeStartHourUtc) + ",\"rangeEndHourUtc\":" + IntegerToString(effectiveTokyoRangeEndHourUtc) + ",\"tradeStartHourUtc\":" + IntegerToString(effectiveTokyoTradeStartHourUtc) + ",\"tradeEndHourUtc\":" + IntegerToString(effectiveTokyoTradeEndHourUtc) + ",\"lookbackBars\":" + IntegerToString(effectiveTokyoLookbackBars) + ",\"bufferPips\":" + FormatNumber(effectiveTokyoBufferPips, 2) + "},";
   json += "\"nightReversion\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(nightTimeframe)) + "\",\"startHourUtc\":" + IntegerToString(effectiveNightStartHourUtc) + ",\"endHourUtc\":" + IntegerToString(effectiveNightEndHourUtc) + ",\"bollingerPeriod\":" + IntegerToString(effectiveNightBollingerPeriod) + ",\"deviations\":" + FormatNumber(effectiveNightDeviations, 4) + ",\"entryBufferPips\":" + FormatNumber(effectiveNightEntryBufferPips, 2) + "},";
   json += "\"h4Pullback\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(h4TrendTimeframe)) + "\",\"fastEmaPeriod\":" + IntegerToString(effectiveH4FastEmaPeriod) + ",\"slowEmaPeriod\":" + IntegerToString(effectiveH4SlowEmaPeriod) + ",\"pullbackEmaPeriod\":" + IntegerToString(effectiveH4PullbackEmaPeriod) + ",\"rsiPeriod\":" + IntegerToString(effectiveH4RsiPeriod) + ",\"longRsiMin\":" + FormatNumber(effectiveH4LongRsiMin, 2) + ",\"shortRsiMax\":" + FormatNumber(effectiveH4ShortRsiMax, 2) + "}";
   json += "},";
   json += "\"tokyoRange\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(tokyoTimeframe)) + "\",";
   json += "\"eventBarTime\":\"" + JsonEscape(FormatDateTime(tokyoEventBarTime, true)) + "\",";
   json += "\"windowActive\":" + JsonBool(tokyoWindowActive) + ",";
   json += "\"boxReady\":" + JsonBool(tokyoBoxReady) + ",";
   json += "\"boxSamples\":" + IntegerToString(tokyoSamples) + ",";
   json += "\"boxHigh\":" + FormatNumber(tokyoBoxHigh, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"boxLow\":" + FormatNumber(tokyoBoxLow, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"boxPips\":" + FormatNumber(tokyoBoxPips, 2) + ",";
   json += "\"bufferPips\":" + FormatNumber(tokyoBufferPips, 2) + ",";
   json += "\"adx\":" + FormatNumber(tokyoAdx, 2) + ",";
   json += "\"adxPass\":" + JsonBool(tokyoAdxPass) + ",";
   json += "\"breakoutLong\":" + JsonBool(tokyoBreakoutLong) + ",";
   json += "\"breakoutShort\":" + JsonBool(tokyoBreakoutShort) + ",";
   json += "\"nearLong\":" + JsonBool(tokyoNearLong) + ",";
   json += "\"nearShort\":" + JsonBool(tokyoNearShort) + ",";
   json += "\"signalDirection\":" + IntegerToString(tokyoSignalDirection) + ",";
   json += "\"score\":" + FormatNumber(tokyoScore, 1) + "},";
   json += "\"nightReversion\":{\"timeframe\":\"" + JsonEscape(TimeframeLabel(nightTimeframe)) + "\",";
   json += "\"eventBarTime\":\"" + JsonEscape(FormatDateTime(nightEventBarTime, true)) + "\",";
   json += "\"windowActive\":" + JsonBool(nightWindowActive) + ",";
   json += "\"indicatorReady\":" + JsonBool(nightIndicatorReady) + ",";
   json += "\"rangeRegime\":" + JsonBool(nightRangeRegime) + ",";
   json += "\"regime\":\"" + JsonEscape(nightRegime.label) + "\",";
   json += "\"rsi\":" + FormatNumber(nightRsi1, 2) + ",";
   json += "\"upperBand\":" + FormatNumber(nightUpperBand, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"lowerBand\":" + FormatNumber(nightLowerBand, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"atr\":" + FormatNumber(nightAtr1, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"adx\":" + FormatNumber(nightAdx, 2) + ",";
   json += "\"adxPass\":" + JsonBool(nightAdxPass) + ",";
   json += "\"strictLong\":" + JsonBool(nightStrictLong) + ",";
   json += "\"strictShort\":" + JsonBool(nightStrictShort) + ",";
   json += "\"softLong\":" + JsonBool(nightSoftLong) + ",";
   json += "\"softShort\":" + JsonBool(nightSoftShort) + ",";
   json += "\"signalDirection\":" + IntegerToString(nightSignalDirection) + ",";
   json += "\"score\":" + FormatNumber(nightScore, 1) + "},";
   json += "\"h4Pullback\":{\"signalTimeframe\":\"" + JsonEscape(TimeframeLabel(h4SignalTimeframe)) + "\",";
   json += "\"trendTimeframe\":\"H4\",";
   json += "\"eventBarTime\":\"" + JsonEscape(FormatDateTime(h4EventBarTime, true)) + "\",";
   json += "\"historyReady\":" + JsonBool(h4HistoryReady) + ",";
   json += "\"indicatorReady\":" + JsonBool(h4IndicatorReady) + ",";
   json += "\"h4Close\":" + FormatNumber(h4Close1, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"h4Ema50\":" + FormatNumber(h4Ema50, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"h4Ema200\":" + FormatNumber(h4Ema200, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"m15FastEma\":" + FormatNumber(h4M15FastEma, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"m15SlowEma\":" + FormatNumber(h4M15SlowEma, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"m15Atr\":" + FormatNumber(h4M15Atr1, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"m15Rsi\":" + FormatNumber(h4Rsi1, 2) + ",";
   json += "\"m15RsiPrev\":" + FormatNumber(h4Rsi2, 2) + ",";
   json += "\"longTrend\":" + JsonBool(h4LongTrend) + ",";
   json += "\"shortTrend\":" + JsonBool(h4ShortTrend) + ",";
   json += "\"longPullback\":" + JsonBool(h4LongPullback) + ",";
   json += "\"shortPullback\":" + JsonBool(h4ShortPullback) + ",";
   json += "\"signalDirection\":" + IntegerToString(h4SignalDirection) + ",";
   json += "\"score\":" + FormatNumber(h4Score, 1) + "},";
   json += "\"genericStrategy\":{\"implemented\":" + JsonBool(StrategyJsonGenericAdapterFamily(strategyFamily)) + ",";
   json += "\"strategyFamily\":\"" + JsonEscape(strategyFamily) + "\",";
   json += "\"timeframe\":\"" + JsonEscape(TimeframeLabel(genericContractTimeframe)) + "\",";
   json += "\"evalCode\":\"" + JsonEscape(PilotEvalCodeLabel(genericEvalCode)) + "\",";
   json += "\"signalDirection\":" + IntegerToString(genericDirection) + ",";
   json += "\"score\":" + FormatNumber(genericScore, 1) + ",";
   json += "\"hasSignal\":" + JsonBool(genericHasSignal) + ",";
   json += "\"contractSignalMatches\":" + JsonBool(genericContractSignal) + ",";
   json += "\"trigger\":\"" + JsonEscape(genericTrigger) + "\",";
   json += "\"reason\":\"" + JsonEscape(genericReason) + "\",";
   json += "\"slPrice\":" + FormatNumber(genericSL, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"tpPrice\":" + FormatNumber(genericTP, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + "},";
   json += "\"bid\":" + FormatNumber(bid, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"ask\":" + FormatNumber(ask, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
   json += "\"shadowEvaluationOnly\":true,";
   json += "\"orderSendAllowed\":false,";
   json += "\"livePresetMutationAllowed\":false,";
   json += "\"gaDirectLiveAllowed\":false";
   json += "}";
   return json;
}

void WriteStrategyJsonEAShadowEvaluationFiles(string evaluationJson)
{
   static datetime lastWrite = 0;
   datetime now = TimeLocal();
   WriteTextFile(StrategyJsonEAShadowEvaluationStatusFileName(), evaluationJson);
   int intervalSeconds = MathMax(5, StrategyJsonEAContractShadowEvalEverySeconds);
   if(lastWrite > 0 && (now - lastWrite) < intervalSeconds)
      return;
   AppendTextFile(StrategyJsonEAShadowEvaluationLedgerFileName(), evaluationJson + "\r\n");
   lastWrite = now;
}
// Strategy JSON EA Contract Adapter END

string KlineExporterTimeframeLabel(ENUM_TIMEFRAMES timeframe)
{
   if(timeframe == PERIOD_M1)
      return "M1";
   if(timeframe == PERIOD_M5)
      return "M5";
   if(timeframe == PERIOD_M15)
      return "M15";
   if(timeframe == PERIOD_H1)
      return "H1";
   return "UNKNOWN";
}

string KlineExporterSafeSymbol(string symbol)
{
   string safe = symbol;
   StringReplace(safe, "\\", "_");
   StringReplace(safe, "/", "_");
   StringReplace(safe, ":", "_");
   StringReplace(safe, " ", "_");
   return safe;
}

string KlineExporterCsvPath(string symbol, string timeframe)
{
   return "backtest\\exported_klines\\QuantGod_" + KlineExporterSafeSymbol(symbol) + "_" + timeframe + "_rates.csv";
}

int KlineExporterChunkDays(ENUM_TIMEFRAMES timeframe)
{
   if(timeframe == PERIOD_M1)
      return 31;
   if(timeframe == PERIOD_M5)
      return 93;
   if(timeframe == PERIOD_M15)
      return 186;
   return 372;
}

int ExportUsdJpyKlineTimeframe(string symbol,
                               ENUM_TIMEFRAMES timeframe,
                               string timeframeLabel,
                               datetime fromTime,
                               datetime toTime,
                               int maxBars,
                               string &manifestItems)
{
   string csvPath = KlineExporterCsvPath(symbol, timeframeLabel);
   string item = "{";
   item += "\"timeframe\":\"" + JsonEscape(timeframeLabel) + "\",";
   item += "\"file\":\"" + JsonEscape(csvPath) + "\",";
   item += "\"requestedFromServer\":\"" + JsonEscape(FormatDateTime(fromTime, true)) + "\",";
   item += "\"requestedToServer\":\"" + JsonEscape(FormatDateTime(toTime, true)) + "\",";

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   ResetLastError();
   int handle = FileOpen(csvPath,
                         FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE,
                         ',',
                         CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      item += "\"copiedBars\":0,";
      item += "\"ok\":false,";
      item += "\"error\":\"" + JsonEscape("FileOpen failed err=" + IntegerToString(GetLastError())) + "\"";
      item += "}";
      if(StringLen(manifestItems) > 0)
         manifestItems += ",";
      manifestItems += item;
      return 0;
   }

   FileWrite(handle, "epoch", "timestamp", "open", "high", "low", "close", "tick_volume", "spread", "real_volume");

   int chunkDays = KlineExporterChunkDays(timeframe);
   int timeframeSeconds = PeriodSeconds(timeframe);
   if(timeframeSeconds <= 0)
      timeframeSeconds = 60;

   datetime cursor = fromTime;
   datetime lastWrittenTime = 0;
   datetime oldestWritten = 0;
   datetime latestWritten = 0;
   int rowsToWrite = 0;
   int totalCopied = 0;
   int chunkCount = 0;
   int failedChunks = 0;
   bool truncated = false;
   string firstError = "";

   while(cursor < toTime)
   {
      if(maxBars > 0 && rowsToWrite >= maxBars)
      {
         truncated = true;
         break;
      }

      datetime chunkEnd = cursor + chunkDays * 24 * 60 * 60;
      if(chunkEnd > toTime)
         chunkEnd = toTime;
      if(chunkEnd <= cursor)
         chunkEnd = cursor + timeframeSeconds;

      MqlRates rates[];
      ArraySetAsSeries(rates, false);
      ResetLastError();
      int copied = CopyRates(symbol, timeframe, cursor, chunkEnd, rates);
      chunkCount++;
      if(copied <= 0)
      {
         int err = GetLastError();
         if(err != 0)
         {
            failedChunks++;
            if(StringLen(firstError) <= 0)
               firstError = "CopyRates chunk returned " + IntegerToString(copied) + " err=" + IntegerToString(err)
                            + " from=" + FormatDateTime(cursor, true)
                            + " to=" + FormatDateTime(chunkEnd, true);
         }
         cursor = chunkEnd + timeframeSeconds;
         continue;
      }

      totalCopied += copied;
      for(int i = 0; i < copied; i++)
      {
         if(maxBars > 0 && rowsToWrite >= maxBars)
         {
            truncated = true;
            break;
         }
         if(rates[i].time < fromTime || rates[i].time > toTime)
            continue;
         if(lastWrittenTime > 0 && rates[i].time <= lastWrittenTime)
            continue;

         FileWrite(handle,
                   IntegerToString((long)rates[i].time),
                   FormatDateTime(rates[i].time, true),
                   DoubleToString(rates[i].open, digits),
                   DoubleToString(rates[i].high, digits),
                   DoubleToString(rates[i].low, digits),
                   DoubleToString(rates[i].close, digits),
                   IntegerToString((long)rates[i].tick_volume),
                   IntegerToString((long)rates[i].spread),
                   IntegerToString((long)rates[i].real_volume));
         lastWrittenTime = rates[i].time;
         latestWritten = rates[i].time;
         if(oldestWritten <= 0)
            oldestWritten = rates[i].time;
         rowsToWrite++;
      }
      cursor = chunkEnd + timeframeSeconds;
   }
   FileFlush(handle);
   FileClose(handle);

   item += "\"copiedBars\":" + IntegerToString(rowsToWrite) + ",";
   item += "\"chunkCount\":" + IntegerToString(chunkCount) + ",";
   item += "\"totalCopiedByChunks\":" + IntegerToString(totalCopied) + ",";
   item += "\"failedChunks\":" + IntegerToString(failedChunks) + ",";
   item += "\"truncated\":" + (truncated ? "true" : "false") + ",";
   item += "\"ok\":" + (rowsToWrite > 0 ? "true" : "false") + ",";
   if(rowsToWrite > 0)
   {
      item += "\"oldestServer\":\"" + JsonEscape(FormatDateTime(oldestWritten, true)) + "\",";
      item += "\"latestServer\":\"" + JsonEscape(FormatDateTime(latestWritten, true)) + "\"";
   }
   else
   {
      item += "\"error\":\"" + JsonEscape(StringLen(firstError) > 0 ? firstError : "No rows copied from chunked CopyRates") + "\"";
   }
   item += "}";
   if(StringLen(manifestItems) > 0)
      manifestItems += ",";
   manifestItems += item;
   return rowsToWrite;
}

void ExportUsdJpyKlinesIfDue(bool force = false)
{
   if(!EnableUsdJpyKlineExporter)
      return;
   string symbol = g_focusSymbol;
   if(StringLen(symbol) <= 0)
      symbol = "USDJPYc";
   if(StringFind(symbol, "USDJPY") < 0)
      return;

   datetime now = CurrentServerTime();
   int intervalSeconds = MathMax(60, UsdJpyKlineExportIntervalMinutes * 60);
   if(!force && g_lastUsdJpyKlineExport > 0 && (now - g_lastUsdJpyKlineExport) < intervalSeconds)
      return;

   FolderCreate("backtest");
   FolderCreate("backtest\\exported_klines");

   int months = MathMax(1, UsdJpyKlineExportMonths);
   int maxBars = MathMax(1000, UsdJpyKlineExportMaxBarsPerTimeframe);
   datetime fromTime = now - months * 31 * 24 * 60 * 60;
   string items = "";
   int totalRows = 0;
   totalRows += ExportUsdJpyKlineTimeframe(symbol, PERIOD_M1, "M1", fromTime, now, maxBars, items);
   totalRows += ExportUsdJpyKlineTimeframe(symbol, PERIOD_M5, "M5", fromTime, now, maxBars, items);
   totalRows += ExportUsdJpyKlineTimeframe(symbol, PERIOD_M15, "M15", fromTime, now, maxBars, items);
   totalRows += ExportUsdJpyKlineTimeframe(symbol, PERIOD_H1, "H1", fromTime, now, maxBars, items);
   totalRows += ExportUsdJpyKlineTimeframe(symbol, PERIOD_H4, "H4", fromTime, now, maxBars, items);

   string manifest = "{\r\n";
   manifest += "  \"schema\": \"quantgod.mql5_kline_export_manifest.v1\",\r\n";
   manifest += "  \"source\": \"MQL5_COPYRATES_EXPORT\",\r\n";
   manifest += "  \"symbol\": \"" + JsonEscape(symbol) + "\",\r\n";
   manifest += "  \"focusSymbol\": \"USDJPYc\",\r\n";
   manifest += "  \"generatedAtServer\": \"" + JsonEscape(FormatDateTime(now, true)) + "\",\r\n";
   manifest += "  \"generatedAtLocal\": \"" + JsonEscape(FormatDateTime(TimeLocal(), true)) + "\",\r\n";
   manifest += "  \"lookbackMonths\": " + IntegerToString(months) + ",\r\n";
   manifest += "  \"maxBarsPerTimeframe\": " + IntegerToString(maxBars) + ",\r\n";
   manifest += "  \"totalRows\": " + IntegerToString(totalRows) + ",\r\n";
   manifest += "  \"timeframes\": [" + items + "],\r\n";
   manifest += "  \"safety\": {\"orderSendAllowed\": false, \"livePresetMutationAllowed\": false}\r\n";
   manifest += "}\r\n";
   WriteTextFile("backtest\\exported_klines\\QuantGod_USDJPY_KlineExportManifest.json", manifest);
   WriteTextFile("QuantGod_USDJPYKlineExportManifest.json", manifest);
   g_lastUsdJpyKlineExport = now;
   Print("QuantGod USDJPY CopyRates exporter wrote ", totalRows, " bars across M1/M5/M15/H1/H4.");
}

int PriceDigitsForSymbol(string symbol)
{
   if(StringLen(symbol) <= 0)
      return 5;
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(digits <= 0)
      return 5;
   return digits;
}

string TradeTransactionTypeLabel(long transactionType)
{
   if(transactionType == TRADE_TRANSACTION_DEAL_ADD)
      return "DEAL_ADD";
   if(transactionType == TRADE_TRANSACTION_ORDER_ADD)
      return "ORDER_ADD";
   if(transactionType == TRADE_TRANSACTION_ORDER_UPDATE)
      return "ORDER_UPDATE";
   if(transactionType == TRADE_TRANSACTION_ORDER_DELETE)
      return "ORDER_DELETE";
   if(transactionType == TRADE_TRANSACTION_HISTORY_ADD)
      return "HISTORY_ADD";
   if(transactionType == TRADE_TRANSACTION_REQUEST)
      return "REQUEST";
   if(transactionType == TRADE_TRANSACTION_POSITION)
      return "POSITION";
   return "OTHER";
}

string LiveExecutionEventTypeFromDealEntry(long entryType)
{
   if(IsEntryDeal(entryType))
      return "ORDER_FILL";
   if(IsExitDeal(entryType))
      return "ORDER_CLOSE";
   return "ORDER_UPDATE";
}

double SlippagePipsForSide(string symbol, string side, double expectedPrice, double fillPrice)
{
   double pip = PipSize(symbol);
   if(pip <= 0.0 || expectedPrice <= 0.0 || fillPrice <= 0.0)
      return 0.0;
   if(side == "SELL")
      return (expectedPrice - fillPrice) / pip;
   return (fillPrice - expectedPrice) / pip;
}

double ProfitToR(double netProfit)
{
   double riskUnit = MathAbs(PilotMaxFloatingLossUSC);
   if(riskUnit <= 0.0)
      return 0.0;
   return netProfit / riskUnit;
}

string BuildLiveExecutionFeedbackJsonLine(string feedbackId,
                                          string eventType,
                                          string source,
                                          string symbol,
                                          string side,
                                          string strategyId,
                                          string policyId,
                                          string intentId,
                                          ulong orderTicket,
                                          ulong dealTicket,
                                          ulong positionId,
                                          double volume,
                                          double expectedPrice,
                                          double fillPrice,
                                          double slippagePips,
                                          double spreadAtEntry,
                                          int latencyMs,
                                          uint retcode,
                                          int retcodeExternal,
                                          string rejectReason,
                                          string exitReason,
                                          double profitR,
                                          double profitUSC,
                                          double mfeR,
                                          double maeR,
                                          datetime eventTimeServer,
                                          string comment,
                                          string transactionType)
{
   int digits = PriceDigitsForSymbol(symbol);
   string line = "{";
   line += "\"schema\":\"quantgod.live_execution_feedback.v1\",";
   line += "\"feedbackId\":\"" + JsonEscape(feedbackId) + "\",";
   line += "\"generatedAtLocal\":\"" + JsonEscape(FormatDateTime(TimeLocal(), true)) + "\",";
   line += "\"generatedAtServer\":\"" + JsonEscape(FormatDateTime(CurrentServerTime(), true)) + "\",";
   line += "\"eventTimeServer\":\"" + JsonEscape(FormatDateTime(eventTimeServer > 0 ? eventTimeServer : CurrentServerTime(), true)) + "\",";
   line += "\"source\":\"" + JsonEscape(source) + "\",";
   line += "\"eventType\":\"" + JsonEscape(eventType) + "\",";
   line += "\"transactionType\":\"" + JsonEscape(transactionType) + "\",";
   line += "\"symbol\":\"" + JsonEscape(symbol) + "\",";
   line += "\"side\":\"" + JsonEscape(side) + "\",";
   line += "\"strategyId\":\"" + JsonEscape(strategyId) + "\",";
   line += "\"policyId\":\"" + JsonEscape(policyId) + "\",";
   line += "\"intentId\":\"" + JsonEscape(intentId) + "\",";
   line += "\"orderTicket\":" + IntegerToString((long)orderTicket) + ",";
   line += "\"dealTicket\":" + IntegerToString((long)dealTicket) + ",";
   line += "\"positionId\":" + IntegerToString((long)positionId) + ",";
   line += "\"magic\":" + IntegerToString((long)PilotMagic) + ",";
   line += "\"volume\":" + FormatNumber(volume, 2) + ",";
   line += "\"expectedPrice\":" + FormatNumber(expectedPrice, digits) + ",";
   line += "\"fillPrice\":" + FormatNumber(fillPrice, digits) + ",";
   line += "\"slippagePips\":" + FormatNumber(slippagePips, 4) + ",";
   line += "\"spreadAtEntry\":" + FormatNumber(spreadAtEntry, 2) + ",";
   line += "\"latencyMs\":" + IntegerToString(latencyMs) + ",";
   line += "\"retcode\":" + IntegerToString((long)retcode) + ",";
   line += "\"retcodeExternal\":" + IntegerToString(retcodeExternal) + ",";
   line += "\"rejectReason\":\"" + JsonEscape(rejectReason) + "\",";
   line += "\"exitReason\":\"" + JsonEscape(exitReason) + "\",";
   line += "\"profitR\":" + FormatNumber(profitR, 4) + ",";
   line += "\"profitUSC\":" + FormatNumber(profitUSC, 2) + ",";
   line += "\"mfeR\":" + FormatNumber(mfeR, 4) + ",";
   line += "\"maeR\":" + FormatNumber(maeR, 4) + ",";
   line += "\"comment\":\"" + JsonEscape(comment) + "\",";
   line += "\"safety\":{\"eaOwnsExecution\":true,\"frontendCanTrade\":false,\"telegramCommandsAllowed\":false}";
   line += "}";
   return line;
}

void AppendLiveExecutionFeedback(string jsonLine)
{
   AppendTextFile("QuantGod_LiveExecutionFeedback.jsonl", jsonLine + "\r\n");
}

void AppendPilotTradeResultFeedback(string symbol,
                                    int direction,
                                    string strategyKey,
                                    string intentId,
                                    int attempt,
                                    double expectedPrice,
                                    double fillPrice,
                                    double spreadAtEntry,
                                    int latencyMs,
                                    string eventType)
{
   string side = direction > 0 ? "BUY" : (direction < 0 ? "SELL" : "UNKNOWN");
   uint retcode = g_trade.ResultRetcode();
   string rejectReason = "";
   if(eventType == "ORDER_REJECTED" || eventType == "ORDER_RETRY")
      rejectReason = g_trade.ResultComment();
   string feedbackId = "send-" + intentId + "-" + IntegerToString(attempt) + "-" + IntegerToString((long)retcode);
   double slippagePips = SlippagePipsForSide(symbol, side, expectedPrice, fillPrice);
   string line = BuildLiveExecutionFeedbackJsonLine(feedbackId,
                                                    eventType,
                                                    "QuantGod_MultiStrategy.mq5",
                                                    symbol,
                                                    side,
                                                    strategyKey,
                                                    "USDJPY_LIVE_LOOP",
                                                    intentId,
                                                    g_trade.ResultOrder(),
                                                    g_trade.ResultDeal(),
                                                    0,
                                                    g_trade.ResultVolume(),
                                                    expectedPrice,
                                                    fillPrice,
                                                    slippagePips,
                                                    spreadAtEntry,
                                                    latencyMs,
                                                    retcode,
                                                    0,
                                                    rejectReason,
                                                    "",
                                                    0.0,
                                                    0.0,
                                                    0.0,
                                                    0.0,
                                                    CurrentServerTime(),
                                                    PilotTradeComment(strategyKey, direction),
                                                    "ORDER_SEND_RESULT");
   AppendLiveExecutionFeedback(line);
}

void AppendTradeTransactionFeedback(const MqlTradeTransaction& trans, const MqlTradeRequest& request, const MqlTradeResult& result)
{
   ulong dealTicket = trans.deal;
   ulong orderTicket = trans.order;
   ulong positionId = trans.position;
   ulong magic = request.magic;
   string symbol = trans.symbol;
   string comment = request.comment;
   long dealType = -1;
   long entryType = -1;
   double netProfit = 0.0;
   double volume = trans.volume;
   double fillPrice = trans.price;
   datetime eventTime = CurrentServerTime();

   if(dealTicket != 0 && HistoryDealSelect(dealTicket))
   {
      symbol = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
      dealType = HistoryDealGetInteger(dealTicket, DEAL_TYPE);
      entryType = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      magic = (ulong)HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
      positionId = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      volume = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
      fillPrice = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
      netProfit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT)
                + HistoryDealGetDouble(dealTicket, DEAL_COMMISSION)
                + HistoryDealGetDouble(dealTicket, DEAL_SWAP);
      eventTime = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      string dealComment = HistoryDealGetString(dealTicket, DEAL_COMMENT);
      if(StringLen(TrimString(dealComment)) > 0)
         comment = dealComment;
   }

   if(magic != PilotMagic && request.magic != PilotMagic)
      return;
   if(StringLen(symbol) <= 0)
      symbol = request.symbol;

   string side = "UNKNOWN";
   if(dealType == DEAL_TYPE_BUY || request.type == ORDER_TYPE_BUY)
      side = "BUY";
   else if(dealType == DEAL_TYPE_SELL || request.type == ORDER_TYPE_SELL)
      side = "SELL";

   string eventType = LiveExecutionEventTypeFromDealEntry(entryType);
   if(trans.type == TRADE_TRANSACTION_REQUEST && result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED)
      eventType = "ORDER_REJECTED";
   string strategyId = InferStrategyFromComment(comment);
   double expectedPrice = request.price;
   if(expectedPrice <= 0.0)
   {
      if(side == "BUY")
         expectedPrice = result.ask;
      else if(side == "SELL")
         expectedPrice = result.bid;
   }
   double spreadAtEntry = 0.0;
   if(result.ask > 0.0 && result.bid > 0.0)
      spreadAtEntry = CalcSpreadPips(symbol, result.bid, result.ask);
   double slippagePips = SlippagePipsForSide(symbol, side, expectedPrice, fillPrice);
   string intentId = "tx-" + IntegerToString((long)orderTicket) + "-" + IntegerToString((long)dealTicket);
   string feedbackId = intentId + "-" + eventType + "-" + TradeTransactionTypeLabel(trans.type);
   string rejectReason = "";
   if(eventType == "ORDER_REJECTED")
      rejectReason = result.comment;
   string exitReason = IsExitDeal(entryType) ? "BROKER_DEAL_EXIT" : "";

   string line = BuildLiveExecutionFeedbackJsonLine(feedbackId,
                                                    eventType,
                                                    "QuantGod_MultiStrategy.mq5",
                                                    symbol,
                                                    side,
                                                    strategyId,
                                                    "USDJPY_LIVE_LOOP",
                                                    intentId,
                                                    orderTicket,
                                                    dealTicket,
                                                    positionId,
                                                    volume,
                                                    expectedPrice,
                                                    fillPrice,
                                                    slippagePips,
                                                    spreadAtEntry,
                                                    0,
                                                    result.retcode,
                                                    result.retcode_external,
                                                    rejectReason,
                                                    exitReason,
                                                    ProfitToR(netProfit),
                                                    netProfit,
                                                    0.0,
                                                    0.0,
                                                    eventTime,
                                                    comment,
                                                    TradeTransactionTypeLabel(trans.type));
   AppendLiveExecutionFeedback(line);
}

string BuildLiveExecutionFeedbackHistoryJsonl(TradeJournalRecord &journal[])
{
   string jsonl = "";
   for(int i = 0; i < ArraySize(journal); i++)
   {
      TradeJournalRecord record = journal[i];
      if(record.source != "EA")
         continue;
      string eventType = (record.eventType == "EXIT") ? "ORDER_CLOSE" : "ORDER_FILL";
      string feedbackId = "history-" + IntegerToString((long)record.dealTicket) + "-" + eventType;
      string intentId = "history-" + IntegerToString((long)record.positionId);
      string exitReason = (record.eventType == "EXIT") ? "HISTORY_EXIT" : "";
      string line = BuildLiveExecutionFeedbackJsonLine(feedbackId,
                                                       eventType,
                                                       "QuantGod_MultiStrategy.history",
                                                       record.symbol,
                                                       record.side,
                                                       record.strategy,
                                                       "USDJPY_LIVE_LOOP",
                                                       intentId,
                                                       0,
                                                       record.dealTicket,
                                                       record.positionId,
                                                       record.lots,
                                                       0.0,
                                                       record.price,
                                                       0.0,
                                                       0.0,
                                                       0,
                                                       TRADE_RETCODE_DONE,
                                                       0,
                                                       "",
                                                       exitReason,
                                                       ProfitToR(record.netProfit),
                                                       record.netProfit,
                                                       0.0,
                                                       0.0,
                                                       record.eventTime,
                                                       record.comment,
                                                       "HISTORY_DEAL");
      jsonl += line + "\r\n";
   }
   return jsonl;
}

void UpdateShadowChartComment(string tradeStatus, bool connected, long accountLogin)
{
   string message = IsPilotLiveMode() ? "QuantGod MT5 Live Pilot\r\n" : "QuantGod MT5 Shadow\r\n";
   message += "Status: " + tradeStatus + "\r\n";
   message += "ReadOnly: " + (ReadOnlyMode ? "true" : "false") + "\r\n";
   message += "PilotAuto: " + (IsPilotLiveMode() ? "true" : "false") + "\r\n";
   message += "Focus: " + g_focusSymbol + "\r\n";
   message += "Watchlist: " + g_resolvedWatchlist + "\r\n";
   message += "Account: " + IntegerToString((int)accountLogin) + "\r\n";
   message += "Connected: " + (connected ? "true" : "false");
   Comment(message);
}

string BuildTradeJournalCsv(TradeJournalRecord &journal[])
{
   string csv = "DealTicket,PositionId,EventType,Side,Symbol,Lots,Price,GrossProfit,Commission,Swap,NetProfit,EventTime,Strategy,Source,Regime,RegimeTimeframe,Comment\r\n";

   for(int i = 0; i < ArraySize(journal); i++)
   {
      TradeJournalRecord record = journal[i];
      csv += IntegerToString((int)record.dealTicket) + ",";
      csv += IntegerToString((int)record.positionId) + ",";
      csv += CsvEscape(record.eventType) + ",";
      csv += CsvEscape(record.side) + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += FormatNumber(record.lots, 2) + ",";
      csv += FormatNumber(record.price, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(record.grossProfit, 2) + ",";
      csv += FormatNumber(record.commission, 2) + ",";
      csv += FormatNumber(record.swap, 2) + ",";
      csv += FormatNumber(record.netProfit, 2) + ",";
      csv += CsvEscape(FormatDateTime(record.eventTime)) + ",";
      csv += CsvEscape(record.strategy) + ",";
      csv += CsvEscape(record.source) + ",";
      csv += CsvEscape(record.regime) + ",";
      csv += CsvEscape(record.regimeTimeframe) + ",";
      csv += CsvEscape(record.comment) + "\r\n";
   }

   return csv;
}

string BuildCloseHistoryCsv(ClosedTradeRecord &closedTrades[])
{
   string csv = "ExitTicket,PositionId,Type,Symbol,Lots,OpenTime,CloseTime,DurationMinutes,OpenPrice,ClosePrice,GrossProfit,Commission,Swap,NetProfit,Strategy,Source,EntryRegime,ExitRegime,RegimeTimeframe,Comment\r\n";

   for(int i = 0; i < ArraySize(closedTrades); i++)
   {
      ClosedTradeRecord record = closedTrades[i];
      csv += IntegerToString((int)record.ticket) + ",";
      csv += IntegerToString((int)record.positionId) + ",";
      csv += CsvEscape(record.type) + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += FormatNumber(record.lots, 2) + ",";
      csv += CsvEscape(FormatDateTime(record.openTime)) + ",";
      csv += CsvEscape(FormatDateTime(record.closeTime)) + ",";
      csv += IntegerToString(record.durationMinutes) + ",";
      csv += FormatNumber(record.openPrice, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(record.closePrice, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(record.grossProfit, 2) + ",";
      csv += FormatNumber(record.commission, 2) + ",";
      csv += FormatNumber(record.swap, 2) + ",";
      csv += FormatNumber(record.actualProfit, 2) + ",";
      csv += CsvEscape(record.strategy) + ",";
      csv += CsvEscape(record.source) + ",";
      csv += CsvEscape(record.entryRegime) + ",";
      csv += CsvEscape(record.exitRegime) + ",";
      csv += CsvEscape(record.regimeTimeframe) + ",";
      csv += CsvEscape(record.comment) + "\r\n";
   }

   return csv;
}

string BuildTradeOutcomeLabelsCsv(ClosedTradeRecord &closedTrades[])
{
   string csv = "LabelTimeLocal,LabelTimeServer,PositionId,ExitTicket,Symbol,Type,Strategy,Source,OpenTime,CloseTime,DurationMinutes,NetProfit,EntryRegime,ExitRegime,RegimeTimeframe,OutcomeLabel,Comment\r\n";
   datetime serverClock = TimeTradeServer();
   if(serverClock <= 0)
      serverClock = TimeCurrent();

   for(int i = 0; i < ArraySize(closedTrades); i++)
   {
      ClosedTradeRecord record = closedTrades[i];
      string outcome = "FLAT";
      if(record.actualProfit > 0.0)
         outcome = "WIN";
      else if(record.actualProfit < 0.0)
         outcome = "LOSS";

      csv += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
      csv += CsvEscape(FormatDateTime(serverClock, true)) + ",";
      csv += IntegerToString((int)record.positionId) + ",";
      csv += IntegerToString((int)record.ticket) + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += CsvEscape(record.type) + ",";
      csv += CsvEscape(record.strategy) + ",";
      csv += CsvEscape(record.source) + ",";
      csv += CsvEscape(FormatDateTime(record.openTime)) + ",";
      csv += CsvEscape(FormatDateTime(record.closeTime)) + ",";
      csv += IntegerToString(record.durationMinutes) + ",";
      csv += FormatNumber(record.actualProfit, 2) + ",";
      csv += CsvEscape(record.entryRegime) + ",";
      csv += CsvEscape(record.exitRegime) + ",";
      csv += CsvEscape(record.regimeTimeframe) + ",";
      csv += CsvEscape(outcome) + ",";
      csv += CsvEscape(record.comment) + "\r\n";
   }

   return csv;
}

string BuildTradeEventLinksCsv(ClosedTradeRecord &closedTrades[], TradeJournalRecord &journal[])
{
   string csv = "PositionId,Symbol,Strategy,Source,EntryDeal,ExitDeal,OpenTime,CloseTime,DurationMinutes,EntryRegime,ExitRegime,RegimeTimeframe,Status,Comment\r\n";
   string emittedKeys[];
   ArrayResize(emittedKeys, 0);

   for(int i = 0; i < ArraySize(closedTrades); i++)
   {
      ClosedTradeRecord record = closedTrades[i];
      ulong entryTicket = 0;
      FindPositionEntryDeal(record.positionId, entryTicket);
      csv += IntegerToString((int)record.positionId) + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += CsvEscape(record.strategy) + ",";
      csv += CsvEscape(record.source) + ",";
      csv += IntegerToString((int)entryTicket) + ",";
      csv += IntegerToString((int)record.ticket) + ",";
      csv += CsvEscape(FormatDateTime(record.openTime)) + ",";
      csv += CsvEscape(FormatDateTime(record.closeTime)) + ",";
      csv += IntegerToString(record.durationMinutes) + ",";
      csv += CsvEscape(record.entryRegime) + ",";
      csv += CsvEscape(record.exitRegime) + ",";
      csv += CsvEscape(record.regimeTimeframe) + ",";
      csv += CsvEscape("CLOSED") + ",";
      csv += CsvEscape(record.comment) + "\r\n";
      PushString(emittedKeys, IntegerToString((int)record.positionId));
   }

   int totalPositions = PositionsTotal();
   for(int i = 0; i < totalPositions; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      ulong positionId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      string key = IntegerToString((int)positionId);
      bool alreadyEmitted = false;
      for(int e = 0; e < ArraySize(emittedKeys); e++)
      {
         if(emittedKeys[e] == key)
         {
            alreadyEmitted = true;
            break;
         }
      }
      if(alreadyEmitted)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      string strategy = InferStrategyFromComment(comment);
      string source = InferTradeSource(comment);
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int durationMinutes = (int)MathMax(0, (long)((TimeTradeServer() > 0 ? TimeTradeServer() : TimeCurrent()) - openTime) / 60);
      RegimeSnapshot entryRegime = EvaluateRegimeAt(symbol, PERIOD_H1, openTime);
      RegimeSnapshot currentRegime = EvaluateRegimeAt(symbol, PERIOD_H1, 0);
      ulong entryTicket = 0;
      FindPositionEntryDeal(positionId, entryTicket);

      csv += IntegerToString((int)positionId) + ",";
      csv += CsvEscape(symbol) + ",";
      csv += CsvEscape(strategy) + ",";
      csv += CsvEscape(source) + ",";
      csv += IntegerToString((int)entryTicket) + ",";
      csv += "0,";
      csv += CsvEscape(FormatDateTime(openTime)) + ",";
      csv += CsvEscape("") + ",";
      csv += IntegerToString(durationMinutes) + ",";
      csv += CsvEscape(entryRegime.label) + ",";
      csv += CsvEscape(currentRegime.label) + ",";
      csv += CsvEscape(currentRegime.timeframe) + ",";
      csv += CsvEscape("OPEN") + ",";
      csv += CsvEscape(comment) + "\r\n";
   }

   return csv;
}

double DirectionalMovePips(string symbol, string side, double openPrice, double currentPrice)
{
   double pip = PipSize(symbol);
   if(pip <= 0.0 || openPrice <= 0.0 || currentPrice <= 0.0)
      return 0.0;
   if(side == "BUY")
      return (currentPrice - openPrice) / pip;
   if(side == "SELL")
      return (openPrice - currentPrice) / pip;
   return 0.0;
}

string BuildManualAlphaLedgerCsv(ClosedTradeRecord &closedTrades[])
{
   string csv = "PositionId,Status,Symbol,Side,Lots,OpenTime,CloseTime,DurationMinutes,OpenPrice,CurrentOrClosePrice,MovePips,FloatingProfit,NetProfit,EntryRegime,CurrentOrExitRegime,RegimeTimeframe,Source,Comment,LearningUse\r\n";
   datetime serverClock = TimeTradeServer();
   if(serverClock <= 0)
      serverClock = TimeCurrent();

   for(int i = 0; i < ArraySize(closedTrades); i++)
   {
      ClosedTradeRecord record = closedTrades[i];
      if(record.source != "MANUAL")
         continue;

      csv += IntegerToString((int)record.positionId) + ",";
      csv += CsvEscape("CLOSED") + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += CsvEscape(record.type) + ",";
      csv += FormatNumber(record.lots, 2) + ",";
      csv += CsvEscape(FormatDateTime(record.openTime)) + ",";
      csv += CsvEscape(FormatDateTime(record.closeTime)) + ",";
      csv += IntegerToString(record.durationMinutes) + ",";
      csv += FormatNumber(record.openPrice, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(record.closePrice, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(DirectionalMovePips(record.symbol, record.type, record.openPrice, record.closePrice), 1) + ",";
      csv += "0.00,";
      csv += FormatNumber(record.actualProfit, 2) + ",";
      csv += CsvEscape(record.entryRegime) + ",";
      csv += CsvEscape(record.exitRegime) + ",";
      csv += CsvEscape(record.regimeTimeframe) + ",";
      csv += CsvEscape(record.source) + ",";
      csv += CsvEscape(record.comment) + ",";
      csv += CsvEscape("LEARN_ONLY_CLOSED_MANUAL") + "\r\n";
   }

   int totalPositions = PositionsTotal();
   for(int i = 0; i < totalPositions; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      string source = InferTradeSource(comment);
      if(source != "MANUAL")
         continue;

      ulong positionId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      long positionType = PositionGetInteger(POSITION_TYPE);
      string side = PositionTypeToString(positionType);
      double lots = PositionGetDouble(POSITION_VOLUME);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
      if(currentPrice <= 0.0)
      {
         MqlTick tick;
         ZeroMemory(tick);
         if(SymbolInfoTick(symbol, tick))
            currentPrice = (positionType == POSITION_TYPE_BUY) ? tick.bid : tick.ask;
      }
      double floatingProfit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int durationMinutes = (int)MathMax(0, (long)(serverClock - openTime) / 60);
      RegimeSnapshot entryRegime = EvaluateRegimeAt(symbol, PERIOD_H1, openTime);
      RegimeSnapshot currentRegime = EvaluateRegimeAt(symbol, PERIOD_H1, 0);

      csv += IntegerToString((int)positionId) + ",";
      csv += CsvEscape("OPEN") + ",";
      csv += CsvEscape(symbol) + ",";
      csv += CsvEscape(side) + ",";
      csv += FormatNumber(lots, 2) + ",";
      csv += CsvEscape(FormatDateTime(openTime)) + ",";
      csv += CsvEscape("") + ",";
      csv += IntegerToString(durationMinutes) + ",";
      csv += FormatNumber(openPrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(currentPrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ",";
      csv += FormatNumber(DirectionalMovePips(symbol, side, openPrice, currentPrice), 1) + ",";
      csv += FormatNumber(floatingProfit, 2) + ",";
      csv += FormatNumber(floatingProfit, 2) + ",";
      csv += CsvEscape(entryRegime.label) + ",";
      csv += CsvEscape(currentRegime.label) + ",";
      csv += CsvEscape(currentRegime.timeframe) + ",";
      csv += CsvEscape(source) + ",";
      csv += CsvEscape(comment) + ",";
      csv += CsvEscape("LEARN_ONLY_OPEN_MANUAL") + "\r\n";
   }

   return csv;
}

void BuildAggregates(SymbolSnapshot &snapshots[], ClosedTradeRecord &closedTrades[], StrategyAggregateRecord &strategyAggregates[], RegimeAggregateRecord &regimeAggregates[])
{
   ArrayResize(strategyAggregates, 0);
   ArrayResize(regimeAggregates, 0);

   for(int i = 0; i < ArraySize(closedTrades); i++)
   {
      ClosedTradeRecord record = closedTrades[i];
      if(record.source != "EA")
         continue;
      string timeframe = (StringLen(record.regimeTimeframe) > 0) ? record.regimeTimeframe : "H1";

      int strategyIndex = FindStrategyAggregateIndex(strategyAggregates, record.symbol, record.strategy, timeframe);
      if(strategyIndex < 0)
      {
         StrategyAggregateRecord newStrategy;
         newStrategy.symbol = record.symbol;
         newStrategy.strategy = record.strategy;
         newStrategy.timeframe = timeframe;
         newStrategy.closedTrades = 0;
         newStrategy.wins = 0;
         newStrategy.grossProfit = 0.0;
         newStrategy.grossLoss = 0.0;
         newStrategy.netProfit = 0.0;
         newStrategy.lastCloseTime = 0;
         newStrategy.openPositions = 0;
         newStrategy.strategyPositions = 0;
         int newSize = ArraySize(strategyAggregates);
         ArrayResize(strategyAggregates, newSize + 1);
         strategyAggregates[newSize] = newStrategy;
         strategyIndex = newSize;
      }

      strategyAggregates[strategyIndex].closedTrades++;
      if(record.actualProfit > 0.0)
         strategyAggregates[strategyIndex].wins++;
      if(record.actualProfit >= 0.0)
         strategyAggregates[strategyIndex].grossProfit += record.actualProfit;
      else
         strategyAggregates[strategyIndex].grossLoss += MathAbs(record.actualProfit);
      strategyAggregates[strategyIndex].netProfit += record.actualProfit;
      if(record.closeTime > strategyAggregates[strategyIndex].lastCloseTime)
         strategyAggregates[strategyIndex].lastCloseTime = record.closeTime;

      int regimeIndex = FindRegimeAggregateIndex(regimeAggregates, record.symbol, record.strategy, timeframe, record.entryRegime);
      if(regimeIndex < 0)
      {
         RegimeAggregateRecord newRegime;
         newRegime.symbol = record.symbol;
         newRegime.strategy = record.strategy;
         newRegime.timeframe = timeframe;
         newRegime.entryRegime = record.entryRegime;
         newRegime.closedTrades = 0;
         newRegime.linkedTrades = 0;
         newRegime.positiveTrades = 0;
         newRegime.negativeTrades = 0;
         newRegime.flatTrades = 0;
         newRegime.grossProfit = 0.0;
         newRegime.grossLoss = 0.0;
         newRegime.netProfit = 0.0;
         newRegime.totalDurationMinutes = 0.0;
         newRegime.lastEventTime = 0;
         newRegime.lastCloseTime = 0;
         int newSize = ArraySize(regimeAggregates);
         ArrayResize(regimeAggregates, newSize + 1);
         regimeAggregates[newSize] = newRegime;
         regimeIndex = newSize;
      }

      regimeAggregates[regimeIndex].closedTrades++;
      regimeAggregates[regimeIndex].linkedTrades++;
      if(record.actualProfit > 0.0)
         regimeAggregates[regimeIndex].positiveTrades++;
      else if(record.actualProfit < 0.0)
         regimeAggregates[regimeIndex].negativeTrades++;
      else
         regimeAggregates[regimeIndex].flatTrades++;
      if(record.actualProfit >= 0.0)
         regimeAggregates[regimeIndex].grossProfit += record.actualProfit;
      else
         regimeAggregates[regimeIndex].grossLoss += MathAbs(record.actualProfit);
      regimeAggregates[regimeIndex].netProfit += record.actualProfit;
      regimeAggregates[regimeIndex].totalDurationMinutes += record.durationMinutes;
      if(record.openTime > regimeAggregates[regimeIndex].lastEventTime)
         regimeAggregates[regimeIndex].lastEventTime = record.openTime;
      if(record.closeTime > regimeAggregates[regimeIndex].lastCloseTime)
         regimeAggregates[regimeIndex].lastCloseTime = record.closeTime;
   }

   int totalPositions = PositionsTotal();
   for(int i = 0; i < totalPositions; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic))
         continue;
      string strategy = InferStrategyFromComment(comment);
      string timeframe = "H1";
      int strategyIndex = FindStrategyAggregateIndex(strategyAggregates, symbol, strategy, timeframe);
      if(strategyIndex < 0)
      {
         StrategyAggregateRecord newStrategy;
         newStrategy.symbol = symbol;
         newStrategy.strategy = strategy;
         newStrategy.timeframe = timeframe;
         newStrategy.closedTrades = 0;
         newStrategy.wins = 0;
         newStrategy.grossProfit = 0.0;
         newStrategy.grossLoss = 0.0;
         newStrategy.netProfit = 0.0;
         newStrategy.lastCloseTime = 0;
         newStrategy.openPositions = 0;
         newStrategy.strategyPositions = 0;
         int newSize = ArraySize(strategyAggregates);
         ArrayResize(strategyAggregates, newSize + 1);
         strategyAggregates[newSize] = newStrategy;
         strategyIndex = newSize;
      }

      strategyAggregates[strategyIndex].openPositions++;
      strategyAggregates[strategyIndex].strategyPositions++;
   }
}

string BuildStrategyEvaluationCsv(SymbolSnapshot &snapshots[], StrategyAggregateRecord &strategyAggregates[])
{
   string csv = "ReportTimeLocal,ReportTimeServer,Symbol,Strategy,Timeframe,Regime,Enabled,Active,RuntimeLabel,AdaptiveState,AdaptiveReason,RiskMultiplier,TradingStatus,SignalStatus,SignalReason,SignalScore,ClosedTrades,WinRate,ProfitFactor,AvgNet,NetProfit,GrossProfit,GrossLoss,OpenPositions,StrategyPositions,TickAgeSeconds,SpreadPips,ATRPips,ADX,BBWidthPips,LastEvalTime,LastClosedTime\r\n";
   datetime serverClock = TimeTradeServer();
   if(serverClock <= 0)
      serverClock = TimeCurrent();

   for(int i = 0; i < ArraySize(strategyAggregates); i++)
   {
      StrategyAggregateRecord record = strategyAggregates[i];
      double winRate = 0.0;
      double profitFactor = 0.0;
      double avgNet = 0.0;
      if(record.closedTrades > 0)
      {
         winRate = (double)record.wins * 100.0 / (double)record.closedTrades;
         avgNet = record.netProfit / (double)record.closedTrades;
         profitFactor = (record.grossLoss > 0.0) ? (record.grossProfit / record.grossLoss) : (record.grossProfit > 0.0 ? 999.0 : 0.0);
      }

      int symbolIndex = FindSymbolIndex(record.symbol);
      int tickAge = (symbolIndex >= 0) ? snapshots[symbolIndex].tickAgeSeconds : 0;
      double spread = (symbolIndex >= 0) ? snapshots[symbolIndex].spread : 0.0;
      bool isPilotMaRow = (record.strategy == "MA_Cross" && symbolIndex >= 0 && symbolIndex < ArraySize(g_maRuntimeStates));
      StrategyStatusSnapshot pilotState;
      if(isPilotMaRow)
         pilotState = g_maRuntimeStates[symbolIndex];

      csv += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
      csv += CsvEscape(FormatDateTime(serverClock, true)) + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += CsvEscape(record.strategy) + ",";
      csv += CsvEscape(record.timeframe) + ",";
      csv += CsvEscape("ALL") + ",";
      csv += (isPilotMaRow && IsPilotLiveMode() ? "true," : "false,");
      csv += (isPilotMaRow ? (pilotState.active ? "true," : "false,") : "false,");
      csv += CsvEscape(isPilotMaRow ? pilotState.runtimeLabel : "SHADOW") + ",";
      csv += CsvEscape(isPilotMaRow ? pilotState.adaptiveState : "WARMUP") + ",";
      csv += CsvEscape(isPilotMaRow ? pilotState.adaptiveReason : "MT5 shadow journaling only") + ",";
      csv += FormatNumber(isPilotMaRow ? pilotState.riskMultiplier : 0.00, 2) + ",";
      csv += CsvEscape(isPilotMaRow ? (g_pilotKillSwitch ? "AUTO_PAUSED" : "READY") : "SHADOW") + ",";
      csv += CsvEscape(isPilotMaRow ? pilotState.status : "NO_DATA") + ",";
      csv += CsvEscape(isPilotMaRow ? pilotState.reason : "HFM MT5 shadow journaling active") + ",";
      csv += FormatNumber(isPilotMaRow ? pilotState.score : 0.0, 1) + ",";
      csv += IntegerToString(record.closedTrades) + ",";
      csv += FormatNumber(winRate, 1) + ",";
      csv += FormatNumber(profitFactor, 2) + ",";
      csv += FormatNumber(avgNet, 2) + ",";
      csv += FormatNumber(record.netProfit, 2) + ",";
      csv += FormatNumber(record.grossProfit, 2) + ",";
      csv += FormatNumber(record.grossLoss, 2) + ",";
      csv += IntegerToString(record.openPositions) + ",";
      csv += IntegerToString(record.strategyPositions) + ",";
      csv += IntegerToString(tickAge) + ",";
      csv += FormatNumber(spread, 1) + ",";
      csv += "0.0,0.0,0.0,";
      csv += CsvEscape(FormatDateTime(serverClock, true)) + ",";
      csv += CsvEscape(FormatDateTime(record.lastCloseTime)) + "\r\n";
   }

   return csv;
}

string BuildRegimeEvaluationCsv(ClosedTradeRecord &closedTrades[], RegimeAggregateRecord &regimeAggregates[])
{
   string csv = "ReportTimeLocal,ReportTimeServer,Symbol,Strategy,Timeframe,EntryRegime,ClosedTrades,LinkedTrades,LinkCoverage,WinRate,ProfitFactor,AvgNet,NetProfit,GrossProfit,GrossLoss,AvgDurationMinutes,AvgSignalScore,PositiveTrades,NegativeTrades,FlatTrades,LastEventTime,LastCloseTime\r\n";
   datetime serverClock = TimeTradeServer();
   if(serverClock <= 0)
      serverClock = TimeCurrent();

   for(int i = 0; i < ArraySize(regimeAggregates); i++)
   {
      RegimeAggregateRecord record = regimeAggregates[i];
      double winRate = 0.0;
      double profitFactor = 0.0;
      double avgNet = 0.0;
      double avgDuration = 0.0;
      double linkCoverage = 0.0;
      if(record.closedTrades > 0)
      {
         winRate = (double)record.positiveTrades * 100.0 / (double)record.closedTrades;
         avgNet = record.netProfit / (double)record.closedTrades;
         avgDuration = record.totalDurationMinutes / (double)record.closedTrades;
         linkCoverage = (double)record.linkedTrades / (double)record.closedTrades;
         profitFactor = (record.grossLoss > 0.0) ? (record.grossProfit / record.grossLoss) : (record.grossProfit > 0.0 ? 999.0 : 0.0);
      }

      csv += CsvEscape(FormatDateTime(TimeLocal(), true)) + ",";
      csv += CsvEscape(FormatDateTime(serverClock, true)) + ",";
      csv += CsvEscape(record.symbol) + ",";
      csv += CsvEscape(record.strategy) + ",";
      csv += CsvEscape(record.timeframe) + ",";
      csv += CsvEscape(record.entryRegime) + ",";
      csv += IntegerToString(record.closedTrades) + ",";
      csv += IntegerToString(record.linkedTrades) + ",";
      csv += FormatNumber(linkCoverage, 2) + ",";
      csv += FormatNumber(winRate, 1) + ",";
      csv += FormatNumber(profitFactor, 2) + ",";
      csv += FormatNumber(avgNet, 2) + ",";
      csv += FormatNumber(record.netProfit, 2) + ",";
      csv += FormatNumber(record.grossProfit, 2) + ",";
      csv += FormatNumber(record.grossLoss, 2) + ",";
      csv += FormatNumber(avgDuration, 1) + ",";
      csv += "0.0,";
      csv += IntegerToString(record.positiveTrades) + ",";
      csv += IntegerToString(record.negativeTrades) + ",";
      csv += IntegerToString(record.flatTrades) + ",";
      csv += CsvEscape(FormatDateTime(record.lastEventTime)) + ",";
      csv += CsvEscape(FormatDateTime(record.lastCloseTime)) + "\r\n";
   }

   return csv;
}

void ExportShadowCsvs(SymbolSnapshot &snapshots[], TradeJournalRecord &journal[], ClosedTradeRecord &closedTrades[])
{
   StrategyAggregateRecord strategyAggregates[];
   RegimeAggregateRecord regimeAggregates[];
   BuildAggregates(snapshots, closedTrades, strategyAggregates, regimeAggregates);

   WriteTextFile("QuantGod_TradeJournal.csv", BuildTradeJournalCsv(journal));
   WriteTextFile("QuantGod_LiveExecutionFeedbackHistory.jsonl", BuildLiveExecutionFeedbackHistoryJsonl(journal));
   WriteTextFile("QuantGod_CloseHistory.csv", BuildCloseHistoryCsv(closedTrades));
   WriteTextFile("QuantGod_TradeOutcomeLabels.csv", BuildTradeOutcomeLabelsCsv(closedTrades));
   WriteTextFile("QuantGod_TradeEventLinks.csv", BuildTradeEventLinksCsv(closedTrades, journal));
   WriteTextFile("QuantGod_ManualAlphaLedger.csv", BuildManualAlphaLedgerCsv(closedTrades));
   WriteTextFile("QuantGod_ShadowOutcomeLedger.csv", BuildShadowOutcomeLedgerCsv());
   WriteTextFile("QuantGod_ShadowCandidateOutcomeLedger.csv", BuildShadowCandidateOutcomeLedgerCsv());
   WriteTextFile("QuantGod_StrategyEvaluationReport.csv", BuildStrategyEvaluationCsv(snapshots, strategyAggregates));
   WriteTextFile("QuantGod_RegimeEvaluationReport.csv", BuildRegimeEvaluationCsv(closedTrades, regimeAggregates));
   WriteTextFile("QuantGod_OpportunityLabels.csv", "EventId,LabelTimeLocal,LabelTimeServer,EventTimeServer,EventBarTime,Symbol,Strategy,Timeframe,SignalStatus,SignalDirection,SignalScore,Regime,AdaptiveState,RiskMultiplier,HorizonBars,ReferencePrice,FutureClose,LongClosePips,ShortClosePips,LongMFEPips,LongMAEPips,ShortMFEPips,ShortMAEPips,NeutralThresholdPips,DirectionalOutcome,BestOpportunity,LabelReason\r\n");
}

void InitializeSnapshots(SymbolSnapshot &snapshots[])
{
   ArrayResize(snapshots, ArraySize(g_symbols));

   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      snapshots[i].symbol = g_symbols[i];
      snapshots[i].role = (i == 0) ? "focus" : "managed";
      snapshots[i].status = "READY";
      snapshots[i].tickAgeSeconds = 0;
      snapshots[i].bid = 0.0;
      snapshots[i].ask = 0.0;
      snapshots[i].spread = 0.0;
      snapshots[i].openPositions = 0;
      snapshots[i].floatingProfit = 0.0;
      snapshots[i].actualFloatingProfit = 0.0;
      snapshots[i].closedTrades = 0;
      snapshots[i].wins = 0;
      snapshots[i].closedProfit = 0.0;
      snapshots[i].actualClosedProfit = 0.0;
      snapshots[i].lastCloseTime = 0;

      MqlTick tick;
      if(SymbolInfoTick(g_symbols[i], tick))
      {
         snapshots[i].bid = tick.bid;
         snapshots[i].ask = tick.ask;
         snapshots[i].spread = CalcSpreadPips(g_symbols[i], tick.bid, tick.ask);
         snapshots[i].tickAgeSeconds = (int)MathMax(0, (long)(TimeCurrent() - (datetime)tick.time));
      }
   }
}

string BuildOpenTradesJson(SymbolSnapshot &snapshots[])
{
   string items[];
   ArrayResize(items, 0);

   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      int symbolIndex = FindSymbolIndex(symbol);

      ulong positionId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      double volume = PositionGetDouble(POSITION_VOLUME);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double profit = PositionGetDouble(POSITION_PROFIT);
      double swap = PositionGetDouble(POSITION_SWAP);
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      string comment = PositionGetString(POSITION_COMMENT);
      string strategy = InferStrategyFromComment(comment);
      string source = InferTradeSource(comment);
      string typeText = PositionTypeToString(PositionGetInteger(POSITION_TYPE));
      int durationMinutes = (int)MathMax(0, (long)((TimeTradeServer() > 0 ? TimeTradeServer() : TimeCurrent()) - openTime) / 60);
      RegimeSnapshot entryRegime = EvaluateRegimeAt(symbol, PERIOD_H1, openTime);
      RegimeSnapshot currentRegime = EvaluateRegimeAt(symbol, PERIOD_H1, 0);

      if(symbolIndex >= 0)
      {
         snapshots[symbolIndex].openPositions++;
         snapshots[symbolIndex].floatingProfit += profit;
         snapshots[symbolIndex].actualFloatingProfit += profit;
         snapshots[symbolIndex].status = "IN_POSITION";
      }

      string json = "    {";
      json += "\"ticket\": " + IntegerToString((int)ticket) + ", ";
      json += "\"positionId\": " + IntegerToString((int)positionId) + ", ";
      json += "\"type\": \"" + typeText + "\", ";
      json += "\"symbol\": \"" + JsonEscape(symbol) + "\", ";
      json += "\"lots\": " + FormatNumber(volume, 2) + ", ";
      json += "\"actualLots\": " + FormatNumber(volume, 2) + ", ";
      json += "\"virtualLots\": " + FormatNumber(volume, 2) + ", ";
      json += "\"openPrice\": " + FormatNumber(openPrice, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"sl\": " + FormatNumber(sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"tp\": " + FormatNumber(tp, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"profit\": " + FormatNumber(profit, 2) + ", ";
      json += "\"actualProfit\": " + FormatNumber(profit, 2) + ", ";
      json += "\"swap\": " + FormatNumber(swap, 2) + ", ";
      json += "\"openTime\": \"" + FormatDateTime(openTime) + "\", ";
      json += "\"durationMinutes\": " + IntegerToString(durationMinutes) + ", ";
      json += "\"strategy\": \"" + JsonEscape(strategy) + "\", ";
      json += "\"source\": \"" + source + "\", ";
      json += "\"entryRegime\": \"" + entryRegime.label + "\", ";
      json += "\"regime\": \"" + currentRegime.label + "\", ";
      json += "\"regimeTimeframe\": \"" + currentRegime.timeframe + "\", ";
      json += "\"comment\": \"" + JsonEscape(comment) + "\"";
      json += "}";

      PushString(items, json);
   }

   string json = "[";
   for(int i = 0; i < ArraySize(items); i++)
   {
      if(i > 0)
         json += ",";
      json += "\r\n" + items[i];
   }
   if(ArraySize(items) > 0)
      json += "\r\n";
   json += "  ]";
   return json;
}

void CollectTradeJournal(TradeJournalRecord &journal[])
{
   ArrayResize(journal, 0);

   datetime historyNow = TimeTradeServer();
   if(historyNow <= 0)
      historyNow = TimeCurrent();
   if(historyNow <= 0)
      historyNow = TimeLocal();

   datetime fromTime = historyNow - (HistoryLookbackDays * 86400);
   if(!HistorySelect(fromTime, historyNow))
      return;

   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0)
         continue;

      string symbol = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
      if(StringLen(symbol) == 0)
         continue;

      long dealType = HistoryDealGetInteger(dealTicket, DEAL_TYPE);
      if(dealType != DEAL_TYPE_BUY && dealType != DEAL_TYPE_SELL)
         continue;

      long entryType = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      string comment = HistoryDealGetString(dealTicket, DEAL_COMMENT);
      string attributionComment = comment;
      ulong positionId = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      if(IsExitDeal(entryType))
      {
         ulong entryTicket = 0;
         FindPositionEntryDeal(positionId, entryTicket);
         if(entryTicket != 0)
         {
            string entryComment = HistoryDealGetString(entryTicket, DEAL_COMMENT);
            if(StringLen(TrimString(entryComment)) > 0)
               attributionComment = entryComment;
         }
      }
      RegimeSnapshot regime = EvaluateRegimeAt(symbol, PERIOD_H1, (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME));

      TradeJournalRecord record;
      record.dealTicket = dealTicket;
      record.positionId = positionId;
      record.eventType = IsExitDeal(entryType) ? "EXIT" : "ENTRY";
      record.side = DealEntryToPositionTypeString(dealType);
      record.symbol = symbol;
      record.lots = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
      record.price = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
      record.grossProfit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
      record.commission = HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);
      record.swap = HistoryDealGetDouble(dealTicket, DEAL_SWAP);
      record.netProfit = record.grossProfit + record.commission + record.swap;
      record.eventTime = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      record.strategy = InferStrategyFromComment(attributionComment);
      record.source = InferTradeSource(attributionComment);
      record.comment = comment;
      record.regime = regime.label;
      record.regimeTimeframe = regime.timeframe;

      PushTradeJournal(journal, record);
   }
}

void CollectClosedTrades(SymbolSnapshot &snapshots[], ClosedTradeRecord &closedTrades[])
{
   ArrayResize(closedTrades, 0);

   datetime historyNow = TimeTradeServer();
   if(historyNow <= 0)
      historyNow = TimeCurrent();
   if(historyNow <= 0)
      historyNow = TimeLocal();

   datetime fromTime = historyNow - (HistoryLookbackDays * 86400);
   if(!HistorySelect(fromTime, historyNow))
   {
      Print("QuantGod MT5 skeleton failed HistorySelect err=", GetLastError());
      return;
   }

   int total = HistoryDealsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      if(ArraySize(closedTrades) >= ClosedTradeLimit)
         break;

      ulong exitTicket = HistoryDealGetTicket(i);
      if(exitTicket == 0)
         continue;

      long entryType = HistoryDealGetInteger(exitTicket, DEAL_ENTRY);
      if(!IsExitDeal(entryType))
         continue;

      string symbol = HistoryDealGetString(exitTicket, DEAL_SYMBOL);
      int symbolIndex = FindSymbolIndex(symbol);

      ulong positionId = (ulong)HistoryDealGetInteger(exitTicket, DEAL_POSITION_ID);
      ulong entryTicket = 0;
      FindPositionEntryDeal(positionId, entryTicket);

      datetime closeTime = (datetime)HistoryDealGetInteger(exitTicket, DEAL_TIME);
      double closePrice = HistoryDealGetDouble(exitTicket, DEAL_PRICE);
      double grossProfit = HistoryDealGetDouble(exitTicket, DEAL_PROFIT);
      double commission = HistoryDealGetDouble(exitTicket, DEAL_COMMISSION);
      double swap = HistoryDealGetDouble(exitTicket, DEAL_SWAP);
      double exitProfit = grossProfit + swap + commission;
      double volume = HistoryDealGetDouble(exitTicket, DEAL_VOLUME);
      string exitComment = HistoryDealGetString(exitTicket, DEAL_COMMENT);

      datetime openTime = closeTime;
      double openPrice = closePrice;
      string comment = exitComment;
      string typeText = DealEntryToPositionTypeString(HistoryDealGetInteger(exitTicket, DEAL_TYPE));
      string source = InferTradeSource(comment);

      if(entryTicket != 0)
      {
         openTime = (datetime)HistoryDealGetInteger(entryTicket, DEAL_TIME);
         openPrice = HistoryDealGetDouble(entryTicket, DEAL_PRICE);
         string entryComment = HistoryDealGetString(entryTicket, DEAL_COMMENT);
         if(StringLen(TrimString(entryComment)) > 0)
            comment = entryComment;
         typeText = DealEntryToPositionTypeString(HistoryDealGetInteger(entryTicket, DEAL_TYPE));
         source = InferTradeSource(comment);
      }

      RegimeSnapshot entryRegime = EvaluateRegimeAt(symbol, PERIOD_H1, openTime);
      RegimeSnapshot exitRegime = EvaluateRegimeAt(symbol, PERIOD_H1, closeTime);

      ClosedTradeRecord record;
      record.ticket = exitTicket;
      record.positionId = positionId;
      record.type = typeText;
      record.symbol = symbol;
      record.lots = volume;
      record.actualLots = volume;
      record.virtualLots = volume;
      record.openPrice = openPrice;
      record.closePrice = closePrice;
      record.profit = exitProfit;
      record.actualProfit = exitProfit;
      record.swap = swap;
      record.openTime = openTime;
      record.closeTime = closeTime;
      record.strategy = InferStrategyFromComment(comment);
      record.source = source;
      record.comment = comment;
      record.entryRegime = entryRegime.label;
      record.exitRegime = exitRegime.label;
      record.regimeTimeframe = entryRegime.timeframe;
      record.durationMinutes = (int)MathMax(0, (long)(closeTime - openTime) / 60);
      record.commission = commission;
      record.grossProfit = grossProfit;

      PushClosedTrade(closedTrades, record);

      if(symbolIndex >= 0 && source == "EA")
      {
         snapshots[symbolIndex].closedTrades++;
         if(exitProfit > 0.0)
            snapshots[symbolIndex].wins++;
         snapshots[symbolIndex].closedProfit += exitProfit;
         snapshots[symbolIndex].actualClosedProfit += exitProfit;
         if(closeTime > snapshots[symbolIndex].lastCloseTime)
            snapshots[symbolIndex].lastCloseTime = closeTime;
      }
   }
}

string BuildClosedTradesJson(ClosedTradeRecord &closedTrades[])
{
   string json = "[";

   for(int i = 0; i < ArraySize(closedTrades); i++)
   {
      ClosedTradeRecord record = closedTrades[i];
      if(i > 0)
         json += ",";
      json += "\r\n    {";
      json += "\"ticket\": " + IntegerToString((int)record.ticket) + ", ";
      json += "\"positionId\": " + IntegerToString((int)record.positionId) + ", ";
      json += "\"type\": \"" + record.type + "\", ";
      json += "\"symbol\": \"" + JsonEscape(record.symbol) + "\", ";
      json += "\"lots\": " + FormatNumber(record.lots, 2) + ", ";
      json += "\"actualLots\": " + FormatNumber(record.actualLots, 2) + ", ";
      json += "\"virtualLots\": " + FormatNumber(record.virtualLots, 2) + ", ";
      json += "\"openPrice\": " + FormatNumber(record.openPrice, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"closePrice\": " + FormatNumber(record.closePrice, (int)SymbolInfoInteger(record.symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"profit\": " + FormatNumber(record.profit, 2) + ", ";
      json += "\"actualProfit\": " + FormatNumber(record.actualProfit, 2) + ", ";
      json += "\"swap\": " + FormatNumber(record.swap, 2) + ", ";
      json += "\"openTime\": \"" + FormatDateTime(record.openTime) + "\", ";
      json += "\"closeTime\": \"" + FormatDateTime(record.closeTime) + "\", ";
      json += "\"durationMinutes\": " + IntegerToString(record.durationMinutes) + ", ";
      json += "\"strategy\": \"" + JsonEscape(record.strategy) + "\", ";
      json += "\"source\": \"" + record.source + "\", ";
      json += "\"entryRegime\": \"" + record.entryRegime + "\", ";
      json += "\"exitRegime\": \"" + record.exitRegime + "\", ";
      json += "\"regimeTimeframe\": \"" + record.regimeTimeframe + "\", ";
      json += "\"comment\": \"" + JsonEscape(record.comment) + "\"";
      json += "}";
   }

   if(ArraySize(closedTrades) > 0)
      json += "\r\n";
   json += "  ]";
   return json;
}

string BuildSymbolsJson(SymbolSnapshot &snapshots[])
{
   string json = "[";

   for(int i = 0; i < ArraySize(snapshots); i++)
   {
      SymbolSnapshot snapshot = snapshots[i];
      double winRate = 0.0;
      if(snapshot.closedTrades > 0)
         winRate = (double)snapshot.wins * 100.0 / (double)snapshot.closedTrades;

      if(i > 0)
         json += ",";

      json += "\r\n    {";
      json += "\"symbol\": \"" + JsonEscape(snapshot.symbol) + "\", ";
      json += "\"role\": \"" + snapshot.role + "\", ";
      json += "\"status\": \"" + snapshot.status + "\", ";
      json += "\"tickAgeSeconds\": " + IntegerToString(snapshot.tickAgeSeconds) + ", ";
      json += "\"bid\": " + FormatNumber(snapshot.bid, (int)SymbolInfoInteger(snapshot.symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"ask\": " + FormatNumber(snapshot.ask, (int)SymbolInfoInteger(snapshot.symbol, SYMBOL_DIGITS)) + ", ";
      json += "\"spread\": " + FormatNumber(snapshot.spread, 1) + ", ";
      json += "\"tradeMode\": \"" + JsonEscape(SymbolTradeModeLabel(SymbolInfoInteger(snapshot.symbol, SYMBOL_TRADE_MODE))) + "\", ";
      json += "\"entryTradeAllowed\": " + JsonBool(SymbolEntryTradeAllowed(snapshot.symbol)) + ", ";
      json += "\"openPositions\": " + IntegerToString(snapshot.openPositions) + ", ";
      json += "\"floatingProfit\": " + FormatNumber(snapshot.floatingProfit, 2) + ", ";
      json += "\"actualFloatingProfit\": " + FormatNumber(snapshot.actualFloatingProfit, 2) + ", ";
      json += "\"closedTrades\": " + IntegerToString(snapshot.closedTrades) + ", ";
      json += "\"winRate\": " + FormatNumber(winRate, 1) + ", ";
      json += "\"closedProfit\": " + FormatNumber(snapshot.closedProfit, 2) + ", ";
      json += "\"actualClosedProfit\": " + FormatNumber(snapshot.actualClosedProfit, 2) + ", ";
      json += "\"lastCloseTime\": \"" + FormatDateTime(snapshot.lastCloseTime) + "\", ";
      json += "\"pilotTelemetry\": " + BuildPilotTelemetryJson(i) + ", ";
      json += "\"strategies\": {";

      for(int s = 0; s < ArraySize(g_strategyKeys); s++)
      {
         if(s > 0)
            json += ", ";
         json += "\"" + g_strategyKeys[s] + "\": ";
         json += BuildSymbolStrategyJson(snapshot.symbol, i, g_strategyKeys[s]);
      }

      json += "}";
      json += "}";
   }

   if(ArraySize(snapshots) > 0)
      json += "\r\n";
   json += "  ]";
   return json;
}

string BuildRootStrategiesJson()
{
   string json = "{";

   for(int i = 0; i < ArraySize(g_strategyKeys); i++)
   {
      if(i > 0)
         json += ", ";
      json += "\"" + g_strategyKeys[i] + "\": ";
      json += BuildRootStrategyJson(g_strategyKeys[i]);
   }

   json += "}";
   return json;
}

string BuildDiagnosticsJson()
{
   string json = "{";

   for(int i = 0; i < ArraySize(g_strategyKeys); i++)
   {
      if(i > 0)
         json += ", ";
      json += "\"" + g_strategyKeys[i] + "\": ";
      json += BuildRootDiagnosticJson(g_strategyKeys[i]);
   }

   json += "}";
   return json;
}

string BuildUsdJpyRsiEntryDiagnosticsJson()
{
   string symbol = g_focusSymbol;
   int symbolIndex = FindSymbolIndex(symbol);
   if(symbolIndex < 0 || !IsUsdJpySymbol(symbol))
   {
      symbolIndex = -1;
      for(int i = 0; i < ArraySize(g_symbols); i++)
      {
         if(IsUsdJpySymbol(g_symbols[i]))
         {
            symbol = g_symbols[i];
            symbolIndex = i;
            break;
         }
      }
   }
   if(StringLen(symbol) <= 0)
      symbol = "USDJPYc";

   MqlTick tick;
   ZeroMemory(tick);
   bool tickOk = SymbolInfoTick(symbol, tick);
   double bid = tickOk ? tick.bid : 0.0;
   double ask = tickOk ? tick.ask : 0.0;
   double spreadPips = tickOk ? CalcSpreadPips(symbol, bid, ask) : 0.0;
   bool spreadAllowed = (tickOk && spreadPips <= PilotMaxSpreadPips);

   bool candidateEnabled = IsLegacyPilotRouteCandidateEnabled("RSI_Reversal");
   bool liveEnabled = IsLegacyPilotRouteLiveEnabled("RSI_Reversal");
   bool inScope = (symbolIndex >= 0 && LegacyPilotRouteInScope("RSI_Reversal", symbol));
   bool liveMode = IsPilotLiveMode();
   string permissionBlocker = LiveTradePermissionBlocker(symbol);
   bool permissionOk = (StringLen(permissionBlocker) == 0);
   bool sessionOpen = IsPilotSessionOpen();
   string newsReason = "";
   bool newsBlocked = PilotNewsBlocksSymbol(symbol, newsReason);
   string cooldownReason = "";
   bool cooldownActive = PilotLossCooldownActive(symbol, cooldownReason);
   string startupReason = "";
   bool startupGuardActive = PilotStartupEntryGuardBlocks(symbol, startupReason);
   bool manualBlock = (PilotBlockManualPerSymbol && HasManualPositionOnSymbol(symbol));
   int portfolioPositions = CountPilotPositions();
   int symbolPositions = CountPilotPositions(symbol);

   double rsi1 = RSIValue(symbol, PilotRsiTimeframe, PilotRsiPeriod, 1);
   double rsi2 = RSIValue(symbol, PilotRsiTimeframe, PilotRsiPeriod, 2);
   double lowerBand = BandsValue(symbol, PilotRsiTimeframe, PilotBBPeriod, PilotBBDeviation, 2, 1);
   double upperBand = BandsValue(symbol, PilotRsiTimeframe, PilotBBPeriod, PilotBBDeviation, 1, 1);
   double close1 = iClose(symbol, PilotRsiTimeframe, 1);
   double atr1 = ATRValue(symbol, PilotRsiTimeframe, 14, 1);
   bool indicatorReady = (rsi1 > 0.0 && rsi2 > 0.0 && lowerBand > 0.0 && upperBand > 0.0 && close1 > 0.0);
   double tolerance = MathMax(0.0, PilotRsiBandTolerancePct);
   double crossbackThreshold = MathMax(0.0, PilotRsiCrossbackThreshold);
   bool exactBuyReversal = (rsi2 < PilotRsiOversold && rsi1 > PilotRsiOversold + crossbackThreshold);
   bool buyReversal = (rsi1 <= PilotRsiOversold || exactBuyReversal);
   bool buyBand = (indicatorReady && close1 <= lowerBand * (1.0 + tolerance));
   double buyScore = 0.0;
   if(indicatorReady)
   {
      buyScore = MathMax(0.0, PilotRsiOversold - rsi1) * 2.0;
      if(exactBuyReversal)
         buyScore += 25.0;
      if(buyBand)
         buyScore += 35.0;
      buyScore = MathMin(100.0, buyScore);
   }
   bool exactSellReversal = (rsi2 > PilotRsiOverbought && rsi1 < PilotRsiOverbought - crossbackThreshold);
   bool sellReversal = (rsi1 >= PilotRsiOverbought || exactSellReversal);
   bool sellBand = (indicatorReady && close1 >= upperBand * (1.0 - tolerance));
   double sellScore = 0.0;
   if(indicatorReady)
   {
      sellScore = MathMax(0.0, rsi1 - PilotRsiOverbought) * 2.0;
      if(exactSellReversal)
         sellScore += 25.0;
      if(sellBand)
         sellScore += 35.0;
      sellScore = MathMin(100.0, sellScore);
   }

   int direction = 0;
   double signalScore = 0.0;
   double stopLoss = 0.0;
   double takeProfit = 0.0;
   string evalReason = "";
   string trigger = "";
   int evalCode = PILOT_EVAL_NONE;
   bool hasSignal = EvaluatePilotRsiH1Signal(symbol, direction, signalScore, evalReason, stopLoss, takeProfit, evalCode, trigger);
   bool sellSideDemoted = (PilotRsiSellLiveBlocked && !(bool)MQLInfoInteger(MQL_TESTER));
   string sessionWindowLabel = "全天";
   if(PilotRestrictSession)
      sessionWindowLabel = IntegerToString(PilotSessionStartHour) + "-" + IntegerToString(PilotSessionEndHour);

   string state = "WAITING_RSI_SIGNAL";
   string summary = "RSI 买入路线已恢复，等待 H1 RSI 与布林带同时触发。";
   string whyItems = "";

   if(symbolIndex < 0)
   {
      state = "SYMBOL_MISSING";
      summary = "没有在 watchlist 中找到 USDJPYc，EA 无法评估 RSI 买入路线。";
      AppendEntryDiagnosticReason(whyItems, "SYMBOL_MISSING", "USDJPY 品种未登记", "请确认 Watchlist 包含 USDJPYc。");
   }
   else if(!candidateEnabled)
   {
      state = "ROUTE_DISABLED";
      summary = "RSI 路线没有开启候选/模拟，EA 不会评估买入。";
      AppendEntryDiagnosticReason(whyItems, "ROUTE_DISABLED", "RSI 路线未启用", "EnablePilotRsiH1Live 或候选状态未开启。");
   }
   else if(!inScope)
   {
      state = "ROUTE_DISABLED";
      summary = "RSI 路线只允许 USDJPY，当前品种不在范围内。";
      AppendEntryDiagnosticReason(whyItems, "ROUTE_SCOPE", "品种不在 RSI 路线范围", symbol);
   }
   else if(!liveEnabled)
   {
      state = "ROUTE_NOT_LIVE";
      summary = "RSI 路线只在模拟/候选层，尚未恢复实盘观察。";
      AppendEntryDiagnosticReason(whyItems, "ROUTE_NOT_LIVE", "RSI 未恢复实盘观察", "当前路线不会触发 EA 实盘入场。");
   }
   else if(!liveMode || !permissionOk)
   {
      state = "PERMISSION_BLOCKED";
      summary = "MT5 交易权限没有完全通过，EA 不会入场。";
      AppendEntryDiagnosticReason(whyItems, "TRADE_PERMISSION", "交易权限未通过", StringLen(permissionBlocker) > 0 ? permissionBlocker : "EnablePilotAutoTrading/ReadOnlyMode 未满足。");
   }
   else if(g_pilotKillSwitch)
   {
      state = "KILL_SWITCH";
      summary = "EA 熔断保护打开，禁止新入场。";
      AppendEntryDiagnosticReason(whyItems, "KILL_SWITCH", "熔断保护中", g_pilotKillReason);
   }
   else if(portfolioPositions >= PilotMaxTotalPositions)
   {
      state = "PORTFOLIO_FULL";
      summary = "EA 已达到自动仓位上限，等待释放容量。";
      AppendEntryDiagnosticReason(whyItems, "PORTFOLIO_FULL", "EA 总仓位已满", IntegerToString(portfolioPositions) + "/" + IntegerToString(PilotMaxTotalPositions));
   }
   else if(symbolPositions >= PilotMaxPositionsPerSymbol)
   {
      state = "SYMBOL_POSITION_FULL";
      summary = "USDJPY EA 仓位已满，不会再开同品种新单。";
      AppendEntryDiagnosticReason(whyItems, "SYMBOL_POSITION_FULL", "USDJPY EA 仓位已满", IntegerToString(symbolPositions) + "/" + IntegerToString(PilotMaxPositionsPerSymbol));
   }
   else if(manualBlock)
   {
      state = "MANUAL_POSITION_BLOCK";
      summary = "人工 USDJPY 持仓占用该品种，EA 按设置不叠加。";
      AppendEntryDiagnosticReason(whyItems, "MANUAL_POSITION", "人工持仓占用", "PilotBlockManualPerSymbol=true。");
   }
   else if(cooldownActive)
   {
      state = "LOSS_COOLDOWN";
      summary = "亏损冷却仍在生效，EA 暂停新入场。";
      AppendEntryDiagnosticReason(whyItems, "LOSS_COOLDOWN", "亏损冷却中", cooldownReason);
   }
   else if(newsBlocked)
   {
      state = "NEWS_BLOCK";
      summary = "USDJPY 高影响新闻过滤正在阻断新入场。";
      AppendEntryDiagnosticReason(whyItems, "NEWS_BLOCK", "新闻过滤阻断", newsReason);
   }
   else if(startupGuardActive)
   {
      state = "STARTUP_GUARD";
      summary = "启动保护正在等待最小时间或下一根 H1 K 线。";
      AppendEntryDiagnosticReason(whyItems, "STARTUP_GUARD", "启动保护中", startupReason);
   }
   else if(!sessionOpen)
   {
      state = "SESSION_CLOSED";
      summary = "当前不在 EA 允许入场时段。";
      AppendEntryDiagnosticReason(whyItems, "SESSION_CLOSED", "交易时段未开放", "允许 " + sessionWindowLabel + "。");
   }
   else if(!spreadAllowed)
   {
      state = "SPREAD_BLOCK";
      summary = "点差超过 EA 入场限制，等待点差回落。";
      AppendEntryDiagnosticReason(whyItems, "SPREAD_BLOCK", "点差过高", FormatNumber(spreadPips, 1) + " / " + FormatNumber(PilotMaxSpreadPips, 1) + " pips");
   }
   else if(hasSignal && direction > 0)
   {
      state = "READY_BUY_SIGNAL";
      summary = "RSI 买入信号已触发；EA 守门通过后可按自身逻辑入场。";
      AppendEntryDiagnosticReason(whyItems, "BUY_SIGNAL_READY", "买入信号已触发", evalReason);
   }
   else if(hasSignal && direction < 0 && sellSideDemoted)
   {
      state = "SELL_SIDE_DEMOTED";
      summary = "当前看到 RSI 卖出信号，但卖出侧已降级，实盘只等待买入。";
      AppendEntryDiagnosticReason(whyItems, "SELL_SIDE_DEMOTED", "卖出侧已降级", evalReason);
   }
   else if(symbolIndex >= 0 && symbolIndex < ArraySize(g_pilotTelemetry) && g_pilotTelemetry[symbolIndex].lastStatus == "WAIT_BAR")
   {
      state = "WAITING_NEXT_BAR";
      summary = "EA 已完成守门，正在等待新的已收盘 H1 K 线。";
      AppendEntryDiagnosticReason(whyItems, "WAIT_BAR", "等待新 K 线", g_pilotTelemetry[symbolIndex].lastReason);
   }
   else
   {
      AppendEntryDiagnosticReason(whyItems, "RSI_SIGNAL_NOT_READY", "RSI 买入条件未同时触发", evalReason);
   }

   PilotTelemetrySnapshot telemetry;
   ZeroMemory(telemetry);
   bool hasTelemetry = (symbolIndex >= 0 && symbolIndex < ArraySize(g_pilotTelemetry));
   if(hasTelemetry)
      telemetry = g_pilotTelemetry[symbolIndex];

   string json = "{";
   json += "\"schema\": \"quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1\", ";
   json += "\"generatedAtLocal\": \"" + JsonEscape(FormatDateTime(TimeLocal(), true)) + "\", ";
   json += "\"generatedAtServer\": \"" + JsonEscape(FormatDateTime(CurrentServerTime(), true)) + "\", ";
   json += "\"symbol\": \"" + JsonEscape(symbol) + "\", ";
   json += "\"strategy\": \"RSI_Reversal\", ";
   json += "\"direction\": \"LONG\", ";
   json += "\"parityContractVersion\": \"quantgod.strategy_deep_parity_matrix.v1\", ";
   json += "\"strategyJsonSchema\": \"quantgod.strategy.v1\", ";
   json += "\"inputs\": {";
   json += "\"PilotRsiTimeframe\": \"" + JsonEscape(TimeframeLabel(PilotRsiTimeframe)) + "\", ";
   json += "\"PilotRsiPeriod\": " + IntegerToString(PilotRsiPeriod) + ", ";
   json += "\"PilotRsiOversold\": " + FormatNumber(PilotRsiOversold, 2) + ", ";
   json += "\"PilotRsiOverbought\": " + FormatNumber(PilotRsiOverbought, 2) + ", ";
   json += "\"PilotRsiCrossbackThreshold\": " + FormatNumber(crossbackThreshold, 2) + ", ";
   json += "\"PilotRsiBandTolerancePct\": " + FormatNumber(PilotRsiBandTolerancePct, 4) + ", ";
   json += "\"PilotMaxSpreadPips\": " + FormatNumber(PilotMaxSpreadPips, 1) + ", ";
   json += "\"PilotRestrictSession\": " + JsonBool(PilotRestrictSession) + ", ";
   json += "\"PilotSessionStartHour\": " + IntegerToString(PilotSessionStartHour) + ", ";
   json += "\"PilotSessionEndHour\": " + IntegerToString(PilotSessionEndHour) + "}, ";
   json += "\"state\": \"" + JsonEscape(state) + "\", ";
   json += "\"stateZh\": \"" + JsonEscape(EntryDiagnosticStateZh(state)) + "\", ";
   json += "\"summary\": \"" + JsonEscape(summary) + "\", ";
   json += "\"route\": {";
   json += "\"candidateEnabled\": " + JsonBool(candidateEnabled) + ", ";
   json += "\"liveEnabled\": " + JsonBool(liveEnabled) + ", ";
   json += "\"inScope\": " + JsonBool(inScope) + ", ";
   json += "\"timeframe\": \"" + JsonEscape(TimeframeLabel(PilotRsiTimeframe)) + "\", ";
   json += "\"lastStatus\": \"" + JsonEscape(hasTelemetry ? telemetry.lastStatus : "") + "\", ";
   json += "\"lastReason\": \"" + JsonEscape(hasTelemetry ? telemetry.lastReason : "") + "\", ";
   json += "\"lastEvalTime\": \"" + JsonEscape(hasTelemetry ? FormatDateTime(telemetry.lastEvalTime, true) : "") + "\", ";
   json += "\"lastSignalTime\": \"" + JsonEscape(hasTelemetry ? FormatDateTime(telemetry.lastSignalTime, true) : "") + "\", ";
   json += "\"lastDirection\": \"" + JsonEscape(hasTelemetry ? PilotDirectionLabel(telemetry.lastDirection) : "NONE") + "\"}, ";
   json += "\"permissions\": {";
   json += "\"liveMode\": " + JsonBool(liveMode) + ", ";
   json += "\"tradeAllowed\": " + JsonBool(permissionOk) + ", ";
   json += "\"blocker\": \"" + JsonEscape(permissionBlocker) + "\", ";
   json += "\"readOnlyMode\": " + JsonBool(ReadOnlyMode) + ", ";
   json += "\"terminalTradeAllowed\": " + JsonBool((bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) + ", ";
   json += "\"programTradeAllowed\": " + JsonBool((bool)MQLInfoInteger(MQL_TRADE_ALLOWED)) + ", ";
   json += "\"accountTradeAllowed\": " + JsonBool((bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)) + ", ";
   json += "\"accountExpertTradeAllowed\": " + JsonBool((bool)AccountInfoInteger(ACCOUNT_TRADE_EXPERT)) + ", ";
   json += "\"symbolTradeMode\": \"" + JsonEscape(SymbolTradeModeLabel(SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE))) + "\"}, ";
   json += "\"guards\": {";
   json += "\"killSwitch\": " + JsonBool(g_pilotKillSwitch) + ", ";
   json += "\"killReason\": \"" + JsonEscape(g_pilotKillReason) + "\", ";
   json += "\"sessionOpen\": " + JsonBool(sessionOpen) + ", ";
   json += "\"sessionWindowUtc\": \"" + JsonEscape(sessionWindowLabel) + "\", ";
   json += "\"spreadAllowed\": " + JsonBool(spreadAllowed) + ", ";
   json += "\"spreadPips\": " + FormatNumber(spreadPips, 1) + ", ";
   json += "\"maxSpreadPips\": " + FormatNumber(PilotMaxSpreadPips, 1) + ", ";
   json += "\"newsBlocked\": " + JsonBool(newsBlocked) + ", ";
   json += "\"newsReason\": \"" + JsonEscape(newsReason) + "\", ";
   json += "\"cooldownActive\": " + JsonBool(cooldownActive) + ", ";
   json += "\"cooldownReason\": \"" + JsonEscape(cooldownReason) + "\", ";
   json += "\"startupGuardActive\": " + JsonBool(startupGuardActive) + ", ";
   json += "\"startupGuardReason\": \"" + JsonEscape(startupReason) + "\", ";
   json += "\"manualPositionBlock\": " + JsonBool(manualBlock) + ", ";
   json += "\"portfolioPositions\": " + IntegerToString(portfolioPositions) + ", ";
   json += "\"maxTotalPositions\": " + IntegerToString(PilotMaxTotalPositions) + ", ";
   json += "\"symbolPositions\": " + IntegerToString(symbolPositions) + ", ";
   json += "\"maxPositionsPerSymbol\": " + IntegerToString(PilotMaxPositionsPerSymbol) + "}, ";
   json += "\"rsi\": {";
   json += "\"indicatorReady\": " + JsonBool(indicatorReady) + ", ";
   json += "\"period\": " + IntegerToString(PilotRsiPeriod) + ", ";
   json += "\"timeframe\": \"" + JsonEscape(TimeframeLabel(PilotRsiTimeframe)) + "\", ";
   json += "\"oversold\": " + FormatNumber(PilotRsiOversold, 2) + ", ";
   json += "\"overbought\": " + FormatNumber(PilotRsiOverbought, 2) + ", ";
   json += "\"buyBandLevel\": " + FormatNumber(PilotRsiOversold, 2) + ", ";
   json += "\"sellBandLevel\": " + FormatNumber(PilotRsiOverbought, 2) + ", ";
   json += "\"crossbackThreshold\": " + FormatNumber(crossbackThreshold, 2) + ", ";
   json += "\"crossbackRule\": \"previous_rsi_outside_band_current_rsi_crosses_band_plus_threshold\", ";
   json += "\"rsiClosed1\": " + FormatNumber(rsi1, 2) + ", ";
   json += "\"rsiClosed2\": " + FormatNumber(rsi2, 2) + ", ";
   json += "\"lowerBand\": " + FormatNumber(lowerBand, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
   json += "\"upperBand\": " + FormatNumber(upperBand, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
   json += "\"closeClosed1\": " + FormatNumber(close1, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
   json += "\"atrClosed1\": " + FormatNumber(atr1, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + ", ";
   json += "\"buyReversal\": " + JsonBool(buyReversal) + ", ";
   json += "\"buyBand\": " + JsonBool(buyBand) + ", ";
   json += "\"buyScore\": " + FormatNumber(buyScore, 1) + ", ";
   json += "\"sellReversal\": " + JsonBool(sellReversal) + ", ";
   json += "\"sellBand\": " + JsonBool(sellBand) + ", ";
   json += "\"sellScore\": " + FormatNumber(sellScore, 1) + ", ";
   json += "\"signalReady\": " + JsonBool(hasSignal) + ", ";
   json += "\"signalDirection\": \"" + JsonEscape(PilotDirectionLabel(direction)) + "\", ";
   json += "\"signalScore\": " + FormatNumber(signalScore, 1) + ", ";
   json += "\"evalCode\": \"" + JsonEscape(PilotEvalCodeLabel(evalCode)) + "\", ";
   json += "\"evalReason\": \"" + JsonEscape(evalReason) + "\", ";
   json += "\"trigger\": \"" + JsonEscape(trigger) + "\"}, ";
   json += "\"whyNoEntry\": [" + whyItems + "]";
   json += "}";
   return json;
}

void ExportDashboard(bool runExecutionLoop)
{
   if(ArraySize(g_symbols) == 0)
      InitializeWatchlist();

   if(runExecutionLoop)
      RunPilotExecutionLoop();

   SymbolSnapshot snapshots[];
   InitializeSnapshots(snapshots);

   TradeJournalRecord journal[];
   CollectTradeJournal(journal);
   ClosedTradeRecord closedTrades[];
   CollectClosedTrades(snapshots, closedTrades);
   string openTradesJson = BuildOpenTradesJson(snapshots);
   string closedTradesJson = BuildClosedTradesJson(closedTrades);
   string symbolsJson = BuildSymbolsJson(snapshots);

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double profit = AccountInfoDouble(ACCOUNT_PROFIT);
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double drawdown = balance - equity;
   if(drawdown < 0.0)
      drawdown = 0.0;

   bool terminalConnected = (bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   bool terminalTradeAllowed = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool programTradeAllowed = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
   bool dllAllowed = (bool)MQLInfoInteger(MQL_DLLS_ALLOWED);
   bool accountTradeAllowed = (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);
   bool accountExpertTradeAllowed = (bool)AccountInfoInteger(ACCOUNT_TRADE_EXPERT);
   long focusSymbolTradeMode = SymbolInfoInteger(g_focusSymbol, SYMBOL_TRADE_MODE);
   bool focusSymbolTradeAllowed = SymbolEntryTradeAllowed(g_focusSymbol);
   string tradePermissionBlocker = LiveTradePermissionBlocker(g_focusSymbol);
   long accountLogin = AccountInfoInteger(ACCOUNT_LOGIN);
   string accountServer = AccountInfoString(ACCOUNT_SERVER);
   bool accountAuthorized = (accountLogin > 0 && StringLen(accountServer) > 0);
   bool connected = (terminalConnected || accountAuthorized);
   bool tradeAllowed = (!ReadOnlyMode && connected && terminalTradeAllowed && programTradeAllowed && accountTradeAllowed && accountExpertTradeAllowed && focusSymbolTradeAllowed);
   string startupGuardReason = "";
   bool startupGuardActive = PilotStartupEntryGuardBlocks(g_focusSymbol, startupGuardReason);
   string tradeStatus = "NO_DATA";
   if(connected)
   {
      if(ReadOnlyMode)
         tradeStatus = "SHADOW";
      else if(StringLen(tradePermissionBlocker) > 0)
      {
         if(StringFind(tradePermissionBlocker, "ACCOUNT_") == 0)
            tradeStatus = "ACCOUNT_TRADE_DISABLED";
         else if(StringFind(tradePermissionBlocker, "SYMBOL_") == 0)
            tradeStatus = "SYMBOL_TRADE_DISABLED";
         else
            tradeStatus = "AUTOTRADING_OFF";
      }
      else if(g_pilotKillSwitch)
         tradeStatus = "AUTO_PAUSED";
      else if(g_newsState.blocked)
         tradeStatus = "NEWS_BLOCK";
      else if(startupGuardActive)
         tradeStatus = "STARTUP_GUARD";
      else if(tradeAllowed)
         tradeStatus = "READY";
      else
         tradeStatus = "AUTOTRADING_OFF";
   }

   datetime serverClock = CurrentServerTime();

   MqlTick focusTick;
   ZeroMemory(focusTick);
   SymbolInfoTick(g_focusSymbol, focusTick);
   double focusBid = focusTick.bid;
   double focusAsk = focusTick.ask;
   double focusSpread = CalcSpreadPips(g_focusSymbol, focusBid, focusAsk);
   int focusTickAge = 0;
   if(connected && focusTick.time > 0)
      focusTickAge = (int)MathMax(0, (long)(serverClock - (datetime)focusTick.time));

   string usdJpyRsiEntryDiagnosticsJson = BuildUsdJpyRsiEntryDiagnosticsJson();
   string strategyJsonEAContractStatusJson = BuildStrategyJsonEAContractStatusJson();
   string strategyJsonEAShadowEvaluationJson = BuildStrategyJsonEAShadowEvaluationJson();
   string autonomousConfigPatchStatusJson = RefreshAutonomousConfigPatchRuntimeAdapter();

   string json = "{\r\n";
   json += "  \"timestamp\": \"" + FormatDateTime(TimeLocal(), true) + "\",\r\n";
   json += "  \"build\": \"" + JsonEscape(DashboardBuild) + "\",\r\n";

   json += "  \"runtime\": {\r\n";
   json += "    \"tradeStatus\": \"" + tradeStatus + "\",\r\n";
   json += "    \"shadowMode\": " + JsonBool(ShadowMode) + ",\r\n";
   json += "    \"readOnlyMode\": " + JsonBool(ReadOnlyMode) + ",\r\n";
   json += "    \"executionEnabled\": " + JsonBool(!ReadOnlyMode) + ",\r\n";
   json += "    \"livePilotMode\": " + JsonBool(IsPilotLiveMode()) + ",\r\n";
   json += "    \"pilotStartupEntryGuard\": " + JsonBool(EnablePilotStartupEntryGuard) + ",\r\n";
   json += "    \"pilotStartupEntryGuardActive\": " + JsonBool(startupGuardActive) + ",\r\n";
   json += "    \"pilotStartupEntryGuardReason\": \"" + JsonEscape(startupGuardReason) + "\",\r\n";
   json += "    \"pilotStartupEntryMinWaitMinutes\": " + IntegerToString(PilotStartupEntryMinWaitMinutes) + ",\r\n";
   json += "    \"pilotStartupEntryWaitNextH1Bar\": " + JsonBool(PilotStartupEntryWaitNextH1Bar) + ",\r\n";
   json += "    \"pilotStartupTime\": \"" + JsonEscape(g_pilotStartupTime > 0 ? FormatDateTime(g_pilotStartupTime, true) : "") + "\",\r\n";
   json += "    \"pilotStartupLocalTime\": \"" + JsonEscape(g_pilotStartupLocalTime > 0 ? FormatDateTime(g_pilotStartupLocalTime, true) : "") + "\",\r\n";
   json += "    \"pilotStartupH1BarTime\": \"" + JsonEscape(g_pilotStartupH1BarTime > 0 ? FormatDateTime(g_pilotStartupH1BarTime, true) : "") + "\",\r\n";
   json += "    \"nonRsiLegacyLiveAuthorization\": " + JsonBool(NonRsiLegacyLiveAuthorizationActive()) + ",\r\n";
   json += "    \"nonRsiLegacyLiveAuthorizationState\": \"" + JsonEscape(NonRsiLegacyLiveAuthorizationState()) + "\",\r\n";
   json += "    \"pilotKillSwitch\": " + JsonBool(g_pilotKillSwitch) + ",\r\n";
   json += "    \"pilotKillReason\": \"" + JsonEscape(g_pilotKillReason) + "\",\r\n";
   json += "    \"pilotRealizedLossToday\": " + FormatNumber(g_pilotRealizedLossToday, 2) + ",\r\n";
   json += "    \"pilotConsecutiveLosses\": " + IntegerToString(g_pilotConsecutiveLosses) + ",\r\n";
   json += "    \"pilotConsecutiveLossPauseMinutes\": " + IntegerToString(PilotConsecutiveLossPauseMinutes) + ",\r\n";
   json += "    \"pilotConsecutiveLossPauseRemainingMinutes\": " + IntegerToString(g_pilotConsecutiveLossPauseRemainingMinutes) + ",\r\n";
   json += "    \"pilotConsecutiveLossPauseExpired\": " + JsonBool(g_pilotConsecutiveLossPauseExpired) + ",\r\n";
   json += "    \"pilotLatestConsecutiveLossTime\": \"" + JsonEscape(g_pilotLatestConsecutiveLossTime > 0 ? FormatDateTime(g_pilotLatestConsecutiveLossTime, true) : "") + "\",\r\n";
   json += "    \"pilotLatestConsecutiveLossNet\": " + FormatNumber(g_pilotLatestConsecutiveLossNet, 2) + ",\r\n";
   json += "    \"pilotFloatingProfit\": " + FormatNumber(SumPilotFloatingProfit(), 2) + ",\r\n";
   json += "    \"connected\": " + JsonBool(connected) + ",\r\n";
   json += "    \"terminalConnected\": " + JsonBool(terminalConnected) + ",\r\n";
   json += "    \"accountAuthorized\": " + JsonBool(accountAuthorized) + ",\r\n";
   json += "    \"terminalTradeAllowed\": " + JsonBool(terminalTradeAllowed) + ",\r\n";
   json += "    \"programTradeAllowed\": " + JsonBool(programTradeAllowed) + ",\r\n";
   json += "    \"accountTradeAllowed\": " + JsonBool(accountTradeAllowed) + ",\r\n";
   json += "    \"accountExpertTradeAllowed\": " + JsonBool(accountExpertTradeAllowed) + ",\r\n";
   json += "    \"focusSymbolTradeAllowed\": " + JsonBool(focusSymbolTradeAllowed) + ",\r\n";
   json += "    \"focusSymbolTradeMode\": \"" + JsonEscape(SymbolTradeModeLabel(focusSymbolTradeMode)) + "\",\r\n";
   json += "    \"tradePermissionBlocker\": \"" + JsonEscape(tradePermissionBlocker) + "\",\r\n";
   json += "    \"dllAllowed\": " + JsonBool(dllAllowed) + ",\r\n";
   json += "    \"tradeAllowed\": " + JsonBool(tradeAllowed) + ",\r\n";
   json += "    \"tickAgeSeconds\": " + IntegerToString(focusTickAge) + ",\r\n";
   json += "    \"researchMode\": false,\r\n";
   json += "    \"serverTime\": \"" + FormatDateTime(serverClock, true) + "\",\r\n";
   json += "    \"gmtTime\": \"" + FormatDateTime(TimeGMT(), true) + "\",\r\n";
    json += "    \"localTime\": \"" + FormatDateTime(TimeLocal(), true) + "\"\r\n";
   json += "  },\r\n";

   json += "  \"news\": " + BuildNewsJson() + ",\r\n";

   json += "  \"cloudSync\": {\r\n";
   json += "    \"enabled\": false,\r\n";
   json += "    \"configured\": false,\r\n";
   json += "    \"endpoint\": \"\",\r\n";
   json += "    \"intervalSeconds\": 30,\r\n";
   json += "    \"lastAttemptLocal\": \"\",\r\n";
   json += "    \"lastSuccessLocal\": \"\",\r\n";
   json += "    \"status\": \"DISABLED\",\r\n";
   json += "    \"httpCode\": 0,\r\n";
   json += "    \"message\": \"Cloud sync is disabled in the MT5 phase 1 skeleton\"\r\n";
   json += "  },\r\n";

   json += "  \"account\": {\r\n";
   json += "    \"number\": " + IntegerToString((int)accountLogin) + ",\r\n";
   json += "    \"name\": \"" + JsonEscape(AccountInfoString(ACCOUNT_NAME)) + "\",\r\n";
   json += "    \"server\": \"" + JsonEscape(accountServer) + "\",\r\n";
   json += "    \"currency\": \"" + JsonEscape(AccountInfoString(ACCOUNT_CURRENCY)) + "\",\r\n";
   string accountModeLabel = ShadowMode ? "mt5_shadow" : (IsPilotLiveMode() ? "mt5_live_pilot" : "mt5_runtime");
   json += "    \"mode\": \"" + JsonEscape(accountModeLabel) + "\",\r\n";
   json += "    \"accountMode\": \"" + AccountMarginModeToString(AccountInfoInteger(ACCOUNT_MARGIN_MODE)) + "\",\r\n";
   json += "    \"symbolSuffix\": \"" + JsonEscape(g_detectedSuffix) + "\",\r\n";
   json += "    \"startingBalance\": " + FormatNumber(balance, 2) + ",\r\n";
   json += "    \"riskPercent\": 0.00,\r\n";
   json += "    \"executionLot\": " + FormatNumber(IsPilotLiveMode() ? PilotLotSize : SymbolInfoDouble(g_focusSymbol, SYMBOL_VOLUME_MIN), 2) + ",\r\n";
   json += "    \"balance\": " + FormatNumber(balance, 2) + ",\r\n";
   json += "    \"equity\": " + FormatNumber(equity, 2) + ",\r\n";
   json += "    \"profit\": " + FormatNumber(profit, 2) + ",\r\n";
   json += "    \"margin\": " + FormatNumber(margin, 2) + ",\r\n";
   json += "    \"freeMargin\": " + FormatNumber(freeMargin, 2) + ",\r\n";
   json += "    \"drawdown\": " + FormatNumber(drawdown, 2) + ",\r\n";
   json += "    \"maxDrawdownPercent\": " + FormatNumber(IsPilotLiveMode() ? 0.60 : 0.00, 2) + ",\r\n";
   json += "    \"maxTotalTrades\": " + IntegerToString(IsPilotLiveMode() ? PilotMaxTotalPositions : 0) + ",\r\n";
   json += "    \"leverage\": " + IntegerToString((int)AccountInfoInteger(ACCOUNT_LEVERAGE)) + "\r\n";
   json += "  },\r\n";

   json += "  \"brokerAccount\": {\r\n";
   json += "    \"balance\": " + FormatNumber(balance, 2) + ",\r\n";
   json += "    \"equity\": " + FormatNumber(equity, 2) + ",\r\n";
   json += "    \"profit\": " + FormatNumber(profit, 2) + ",\r\n";
   json += "    \"margin\": " + FormatNumber(margin, 2) + ",\r\n";
   json += "    \"freeMargin\": " + FormatNumber(freeMargin, 2) + ",\r\n";
   json += "    \"drawdown\": " + FormatNumber(drawdown, 2) + ",\r\n";
   json += "    \"server\": \"" + JsonEscape(accountServer) + "\",\r\n";
   json += "    \"leverage\": " + IntegerToString((int)AccountInfoInteger(ACCOUNT_LEVERAGE)) + "\r\n";
   json += "  },\r\n";

   json += "  \"watchlist\": \"" + JsonEscape(g_resolvedWatchlist) + "\",\r\n";
   json += "  \"symbols\": " + symbolsJson + ",\r\n";
   json += "  \"openTrades\": " + openTradesJson + ",\r\n";
   json += "  \"closedTrades\": " + closedTradesJson + ",\r\n";
   json += "  \"strategies\": " + BuildRootStrategiesJson() + ",\r\n";
   json += "  \"diagnostics\": " + BuildDiagnosticsJson() + ",\r\n";
   json += "  \"usdJpyRsiEntryDiagnostics\": " + usdJpyRsiEntryDiagnosticsJson + ",\r\n";
   json += "  \"strategyJsonEaContract\": " + strategyJsonEAContractStatusJson + ",\r\n";
   json += "  \"strategyJsonEaShadowEvaluation\": " + strategyJsonEAShadowEvaluationJson + ",\r\n";
   json += "  \"autonomousConfigPatchEaStatus\": " + autonomousConfigPatchStatusJson + ",\r\n";
   json += "  \"market\": {\r\n";
   json += "    \"symbol\": \"" + JsonEscape(g_focusSymbol) + "\",\r\n";
   json += "    \"bid\": " + FormatNumber(focusBid, (int)SymbolInfoInteger(g_focusSymbol, SYMBOL_DIGITS)) + ",\r\n";
   json += "    \"ask\": " + FormatNumber(focusAsk, (int)SymbolInfoInteger(g_focusSymbol, SYMBOL_DIGITS)) + ",\r\n";
   json += "    \"spread\": " + FormatNumber(focusSpread, 1) + "\r\n";
   json += "  }\r\n";
   json += "}\r\n";

   string statusFile = "build=" + DashboardBuild + "\r\n";
   statusFile += "tradeStatus=" + tradeStatus + "\r\n";
   statusFile += "livePilotMode=" + (IsPilotLiveMode() ? "true" : "false") + "\r\n";
   statusFile += "pilotStartupEntryGuard=" + (EnablePilotStartupEntryGuard ? "true" : "false") + "\r\n";
   statusFile += "pilotStartupEntryGuardActive=" + (startupGuardActive ? "true" : "false") + "\r\n";
   statusFile += "pilotStartupEntryGuardReason=" + startupGuardReason + "\r\n";
   statusFile += "pilotStartupEntryMinWaitMinutes=" + IntegerToString(PilotStartupEntryMinWaitMinutes) + "\r\n";
   statusFile += "pilotStartupEntryWaitNextH1Bar=" + (PilotStartupEntryWaitNextH1Bar ? "true" : "false") + "\r\n";
   statusFile += "pilotStartupTime=" + (g_pilotStartupTime > 0 ? FormatDateTime(g_pilotStartupTime, true) : "") + "\r\n";
   statusFile += "pilotStartupLocalTime=" + (g_pilotStartupLocalTime > 0 ? FormatDateTime(g_pilotStartupLocalTime, true) : "") + "\r\n";
   statusFile += "pilotStartupH1BarTime=" + (g_pilotStartupH1BarTime > 0 ? FormatDateTime(g_pilotStartupH1BarTime, true) : "") + "\r\n";
   statusFile += "nonRsiLegacyLiveAuthorization=" + (NonRsiLegacyLiveAuthorizationActive() ? "true" : "false") + "\r\n";
   statusFile += "nonRsiLegacyLiveAuthorizationState=" + NonRsiLegacyLiveAuthorizationState() + "\r\n";
   statusFile += "pilotKillSwitch=" + (g_pilotKillSwitch ? "true" : "false") + "\r\n";
   statusFile += "pilotKillReason=" + g_pilotKillReason + "\r\n";
   statusFile += "pilotRealizedLossToday=" + FormatNumber(g_pilotRealizedLossToday, 2) + "\r\n";
   statusFile += "pilotConsecutiveLosses=" + IntegerToString(g_pilotConsecutiveLosses) + "\r\n";
   statusFile += "pilotConsecutiveLossPauseMinutes=" + IntegerToString(PilotConsecutiveLossPauseMinutes) + "\r\n";
   statusFile += "pilotConsecutiveLossPauseRemainingMinutes=" + IntegerToString(g_pilotConsecutiveLossPauseRemainingMinutes) + "\r\n";
   statusFile += "pilotConsecutiveLossPauseExpired=" + (g_pilotConsecutiveLossPauseExpired ? "true" : "false") + "\r\n";
   statusFile += "pilotLatestConsecutiveLossTime=" + (g_pilotLatestConsecutiveLossTime > 0 ? FormatDateTime(g_pilotLatestConsecutiveLossTime, true) : "") + "\r\n";
   statusFile += "pilotLatestConsecutiveLossNet=" + FormatNumber(g_pilotLatestConsecutiveLossNet, 2) + "\r\n";
   statusFile += "pilotFloatingProfit=" + FormatNumber(SumPilotFloatingProfit(), 2) + "\r\n";
   string exportNewsReason = g_newsState.reason;
   if(EnablePilotNewsFilter &&
      (g_newsState.calendarAvailable || ArraySize(g_usdTrackedEventIds) > 0) &&
      g_newsState.status == "IDLE" &&
      g_newsState.reason == "USDJPY high-impact news filter is armed")
   {
      exportNewsReason = "No tracked USDJPY event near the current pilot window";
   }
   string exportNewsEvent = SafeNewsEventName(g_newsState.eventName);
   exportNewsReason = SafeNewsReasonText(exportNewsReason);
   statusFile += "newsStatus=" + g_newsState.status + "\r\n";
   statusFile += "newsBias=" + UsdBiasLabel(g_newsState.usdBiasDirection) + "\r\n";
   statusFile += "newsEvent=" + exportNewsEvent + "\r\n";
   statusFile += "newsCurrency=" + g_newsState.eventCurrency + "\r\n";
   statusFile += "newsReason=" + exportNewsReason + "\r\n";
   statusFile += "connected=" + (connected ? "true" : "false") + "\r\n";
   statusFile += "focusSymbol=" + g_focusSymbol + "\r\n";
   statusFile += "watchlist=" + g_resolvedWatchlist + "\r\n";
   statusFile += "account=" + IntegerToString((int)accountLogin) + "\r\n";
   statusFile += "server=" + accountServer + "\r\n";
   int focusIndex = FindSymbolIndex(g_focusSymbol);
   if(focusIndex >= 0 && focusIndex < ArraySize(g_pilotTelemetry))
   {
      PilotTelemetrySnapshot telemetry = g_pilotTelemetry[focusIndex];
      statusFile += "focusEvalPasses=" + IntegerToString(telemetry.evaluationPasses) + "\r\n";
      statusFile += "focusSignalHits=" + IntegerToString(telemetry.signalHits) + "\r\n";
      statusFile += "focusWaitBarSkips=" + IntegerToString(telemetry.waitBarSkips) + "\r\n";
      statusFile += "focusNoCrossMisses=" + IntegerToString(telemetry.noCrossMisses) + "\r\n";
      statusFile += "focusNewsBlocks=" + IntegerToString(telemetry.newsBlocks + telemetry.newsFiltered) + "\r\n";
      statusFile += "focusLastStatus=" + telemetry.lastStatus + "\r\n";
   }
   statusFile += "journalDeals=" + IntegerToString(ArraySize(journal)) + "\r\n";
   statusFile += "closedTrades=" + IntegerToString(ArraySize(closedTrades)) + "\r\n";
   statusFile += "localTime=" + FormatDateTime(TimeLocal(), true) + "\r\n";
   WriteTextFile("QuantGod_MT5_ShadowStatus.txt", statusFile);
   WriteTextFile("QuantGod_USDJPYRsiEntryDiagnostics.json", usdJpyRsiEntryDiagnosticsJson);
   WriteTextFile(StrategyJsonEAContractStatusFileName(), strategyJsonEAContractStatusJson);
   WriteStrategyJsonEAShadowEvaluationFiles(strategyJsonEAShadowEvaluationJson);
   WriteTextFile("QuantGod_AutonomousConfigPatchEAStatus.json", autonomousConfigPatchStatusJson);
   WriteTextFile("QuantGod_Dashboard.json", json);
   ExportShadowCsvs(snapshots, journal, closedTrades);
   UpdateShadowChartComment(tradeStatus, connected, accountLogin);
}

void ReconcileExistingPilotPositions()
{
   int total = PositionsTotal();
   int reconciled = 0;
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      string comment = PositionGetString(POSITION_COMMENT);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsPilotManagedPosition(comment, magic)) continue;
      string symbol = PositionGetString(POSITION_SYMBOL);
      string strategyKey = "";
      if(StringFind(comment, "RSI_Reversal") >= 0) strategyKey = "RSI_Reversal";
      else if(StringFind(comment, "BB_Triple") >= 0) strategyKey = "BB_Triple";
      else if(StringFind(comment, "MACD_Divergence") >= 0) strategyKey = "MACD_Divergence";
      else if(StringFind(comment, "SR_Breakout") >= 0) strategyKey = "SR_Breakout";
      else if(StringFind(comment, "MA_Cross") >= 0) strategyKey = "MA_Cross";

      datetime barOpen = iTime(symbol, PERIOD_H1, 0);
      int idx = FindSymbolIndex(symbol);
      if(idx < 0) continue;
      if(strategyKey == "RSI_Reversal" && barOpen > 0 && idx < ArraySize(g_lastRsiPilotBarTime))
         g_lastRsiPilotBarTime[idx] = barOpen;
      else if(strategyKey == "BB_Triple" && barOpen > 0 && idx < ArraySize(g_lastBBPilotBarTime))
         g_lastBBPilotBarTime[idx] = barOpen;
      else if(strategyKey == "MACD_Divergence" && barOpen > 0 && idx < ArraySize(g_lastMacdPilotBarTime))
         g_lastMacdPilotBarTime[idx] = barOpen;
      else if(strategyKey == "SR_Breakout" && barOpen > 0 && idx < ArraySize(g_lastSRPilotBarTime))
         g_lastSRPilotBarTime[idx] = barOpen;
      reconciled++;
   }
   if(reconciled > 0)
      Print("QuantGod reconcile: adopted ", reconciled, " existing pilot positions");
}

void ReconcileConsecutiveLossesFromHistory()
{
   datetime todayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(todayStart <= 0) return;
   HistorySelect(todayStart, TimeCurrent());
   int total = HistoryDealsTotal();
   int consecutiveLosses = 0;
   for(int i = total - 1; i >= 0; i--)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(dealTicket, DEAL_MAGIC) != PilotMagic) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      double profit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
      if(profit < 0)
         consecutiveLosses++;
      else
         break;
   }
   g_pilotConsecutiveLosses = consecutiveLosses;
   if(consecutiveLosses > 0)
      Print("QuantGod reconcile: restored consecutiveLosses=", consecutiveLosses, " from history");
}

void ReconcileDailyRealizedLossFromHistory()
{
   datetime todayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(todayStart <= 0) return;
   HistorySelect(todayStart, TimeCurrent());
   int total = HistoryDealsTotal();
   double realizedLoss = 0;
   for(int i = total - 1; i >= 0; i--)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(dealTicket, DEAL_MAGIC) != PilotMagic) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      double profit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
      if(profit < 0)
         realizedLoss += MathAbs(profit);
   }
   g_pilotRealizedLossToday = realizedLoss;
   if(realizedLoss > 0)
      Print("QuantGod reconcile: restored realizedLossToday=", DoubleToString(realizedLoss, 2), " from history");
}

void WriteStartupWarmupHeartbeat(string context, string reason)
{
   string timerHeartbeat = "localTime=" + FormatDateTime(TimeLocal(), true) + "\r\n";
   timerHeartbeat += "serverTime=" + FormatDateTime(CurrentServerTime(), true) + "\r\n";
   timerHeartbeat += "refreshIntervalSeconds=" + IntegerToString(MathMax(1, RefreshIntervalSec)) + "\r\n";
   timerHeartbeat += "context=" + context + "\r\n";
   timerHeartbeat += "status=MARKET_DATA_SYNCING\r\n";
   timerHeartbeat += "reason=" + reason + "\r\n";
   timerHeartbeat += "focusSymbol=" + g_focusSymbol + "\r\n";
   timerHeartbeat += "warmupUntil=" + (g_startupWarmupUntil > 0 ? FormatDateTime(g_startupWarmupUntil, true) : "") + "\r\n";
   timerHeartbeat += "account=" + IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN)) + "\r\n";
   timerHeartbeat += "server=" + AccountInfoString(ACCOUNT_SERVER) + "\r\n";
   WriteTextFile("QuantGod_MT5_TimerHeartbeat.txt", timerHeartbeat);
}

bool StartupWarmupActive(string context)
{
   datetime now = TimeLocal();
   if(g_startupWarmupUntil <= 0 || now >= g_startupWarmupUntil)
      return false;

   string reason = "defer heavy export until market data warmup window ends";
   WriteStartupWarmupHeartbeat(context, reason);
   if(now >= g_nextStartupWarmupLog)
   {
      Print("QuantGod startup warmup waiting: ", reason);
      g_nextStartupWarmupLog = now + 30;
   }
   return true;
}

void InitializeWarmupWatchlist()
{
   ArrayResize(g_symbols, 0);
   ArrayResize(g_requestedSymbols, 0);
   string symbol = _Symbol;
   if(StringLen(symbol) == 0)
      symbol = "USDJPYc";
   PushString(g_requestedSymbols, Watchlist);
   PushString(g_symbols, symbol);
   g_focusSymbol = symbol;
   g_resolvedWatchlist = symbol;
   g_detectedSuffix = "";
   if(StringLen(symbol) > 6)
      g_detectedSuffix = StringSubstr(symbol, 6);
}

bool EnsureFullRuntimeInitialized()
{
   if(g_fullRuntimeInitialized)
      return true;

   InitializeWatchlist();
   ArmPilotStartupEntryGuard();
   LoadTrackedUsdCalendarEvents();
   g_fullRuntimeInitialized = true;

   string startupReason = "";
   bool startupGuardActive = PilotStartupEntryGuardBlocks(g_focusSymbol, startupReason);
   Print("QuantGod MT5 runtime initialized. Focus symbol=", g_focusSymbol,
         " watchlist=", g_resolvedWatchlist, " suffix=", g_detectedSuffix,
         " readOnly=", (ReadOnlyMode ? "true" : "false"),
         " livePilot=", (IsPilotLiveMode() ? "true" : "false"),
         " nonRsiLegacyLiveAuthorization=", NonRsiLegacyLiveAuthorizationState(),
         " startupEntryGuard=", (startupGuardActive ? "ACTIVE" : "CLEAR"),
         " startupReason=", startupReason);
   return true;
}

int OnInit()
{
   InitializeWarmupWatchlist();
   int timerSeconds = MathMax(1, RefreshIntervalSec);
   ResetLastError();
   if(!EventSetTimer(timerSeconds))
      Print("QuantGod timer setup failed. seconds=", timerSeconds, " err=", GetLastError());
   g_startupWarmupUntil = TimeLocal() + MathMax(60, MathMax(1, RefreshIntervalSec) * 36);
   WriteStartupWarmupHeartbeat("OnInit", "defer heavy export until market data warmup window ends");
   Print("QuantGod MT5 runtime warmup armed. Focus symbol=", g_focusSymbol,
         " warmupUntil=", FormatDateTime(g_startupWarmupUntil, true));
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   if(!EnsureFullRuntimeInitialized())
      return;
   bool startupWarmupActive = StartupWarmupActive("OnTick");

   datetime now = TimeCurrent();
   RefreshAutonomousConfigPatchRuntimeAdapter();

   // Risk-critical protections: every tick
   ManagePilotBreakevenStops();
   ManagePilotRsiFailFastStops();
   if(g_pilotKillSwitch && PilotCloseOnKillSwitch)
      ClosePilotPositions(g_pilotKillReason);

   if(startupWarmupActive)
      return;

   // Strategy evaluation: 1s cadence
   if(now - g_lastPilotTick >= 1)
   {
      RunPilotExecutionLoop();
      g_lastPilotTick = now;
   }

   // Full dashboard export: 5s cadence
   if(now - g_lastFullExport >= 5)
   {
      ExportDashboard(false);
      ExportUsdJpyKlinesIfDue(false);
      g_lastFullExport = now;
   }
}

void OnTimer()
{
   if(StartupWarmupActive("OnTimer"))
      return;
   if(!EnsureFullRuntimeInitialized())
      return;

   // Timer exports are read-only. Live strategy evaluation stays on OnTick so a
   // no-tick/weekend timer cannot stall dashboard freshness or trigger orders.
   ExportDashboard(false);
   ExportUsdJpyKlinesIfDue(false);
   string timerHeartbeat = "localTime=" + FormatDateTime(TimeLocal(), true) + "\r\n";
   timerHeartbeat += "serverTime=" + FormatDateTime(CurrentServerTime(), true) + "\r\n";
   timerHeartbeat += "refreshIntervalSeconds=" + IntegerToString(MathMax(1, RefreshIntervalSec)) + "\r\n";
   WriteTextFile("QuantGod_MT5_TimerHeartbeat.txt", timerHeartbeat);
}

void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& request, const MqlTradeResult& result)
{
   AppendTradeTransactionFeedback(trans, request, result);
}
