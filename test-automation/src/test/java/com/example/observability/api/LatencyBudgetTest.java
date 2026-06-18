package com.example.observability.api;

import com.example.observability.LatencyBudget;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class LatencyBudgetTest {
    @Test
    void classifiesLatencyAgainstThresholds() {
        LatencyBudget budget = new LatencyBudget(500, 1000);

        assertThat(budget.classify(100)).isEqualTo("OK");
        assertThat(budget.classify(650)).isEqualTo("WARNING");
        assertThat(budget.classify(1500)).isEqualTo("CRITICAL");
    }

    @Test
    void rejectsInvalidThresholds() {
        assertThatThrownBy(() -> new LatencyBudget(1000, 500))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Warning threshold");
    }
}
