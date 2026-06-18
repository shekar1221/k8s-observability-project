package com.example.observability.api;

import com.example.observability.ServicePath;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ServicePathTest {
    @Test
    void exposesKnownFrontendPaths() {
        assertThat(ServicePath.HOME.path()).isEqualTo("/home");
        assertThat(ServicePath.CHECKOUT_DEMO.path()).isEqualTo("/checkout-demo");
        assertThat(ServicePath.HEALTH.path()).isEqualTo("/healthz");
        assertThat(ServicePath.METRICS.path()).isEqualTo("/metrics");
    }
}
