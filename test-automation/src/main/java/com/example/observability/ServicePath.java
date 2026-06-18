package com.example.observability;

public enum ServicePath {
    HOME("/home"),
    CHECKOUT_DEMO("/checkout-demo"),
    HEALTH("/healthz"),
    METRICS("/metrics");

    private final String path;

    ServicePath(String path) {
        this.path = path;
    }

    public String path() {
        return path;
    }
}
