package com.example.observability;

public class LatencyBudget {
    private final long warningThresholdMs;
    private final long criticalThresholdMs;

    public LatencyBudget(long warningThresholdMs, long criticalThresholdMs) {
        if (warningThresholdMs <= 0 || criticalThresholdMs <= 0) {
            throw new IllegalArgumentException("Thresholds must be positive");
        }
        if (warningThresholdMs >= criticalThresholdMs) {
            throw new IllegalArgumentException("Warning threshold must be lower than critical threshold");
        }
        this.warningThresholdMs = warningThresholdMs;
        this.criticalThresholdMs = criticalThresholdMs;
    }

    public String classify(long latencyMs) {
        if (latencyMs >= criticalThresholdMs) {
            return "CRITICAL";
        }
        if (latencyMs >= warningThresholdMs) {
            return "WARNING";
        }
        return "OK";
    }
}
