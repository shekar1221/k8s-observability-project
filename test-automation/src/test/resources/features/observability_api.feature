Feature: Shopping platform observability API checks

  Scenario: Frontend health endpoint is available
    Given the shopping frontend API is available
    When I call "/healthz"
    Then the response status should be 200
    And the response should contain "frontend"

  Scenario: Frontend metrics endpoint exposes Prometheus metrics
    Given the shopping frontend API is available
    When I call "/metrics"
    Then the response status should be 200
    And the response should contain "frontend_http_requests_total"

  Scenario: Frontend home endpoint calls downstream APIs
    Given the shopping frontend API is available
    When I call "/home"
    Then the response status should be 200
    And the response should contain "products"
