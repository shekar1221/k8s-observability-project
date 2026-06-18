package com.example.observability.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;

import static io.restassured.RestAssured.given;
import static org.assertj.core.api.Assertions.assertThat;

public class ApiStepDefinitions {
    private String baseUrl;
    private Response response;

    @Given("the shopping frontend API is available")
    public void theShoppingFrontendApiIsAvailable() {
        baseUrl = System.getProperty("baseUrl", "http://localhost:8080");
    }

    @When("I call {string}")
    public void iCall(String path) {
        response = given()
                .baseUri(baseUrl)
                .relaxedHTTPSValidation()
                .when()
                .get(path);
    }

    @Then("the response status should be {int}")
    public void theResponseStatusShouldBe(int expectedStatus) {
        assertThat(response.statusCode()).isEqualTo(expectedStatus);
    }

    @Then("the response should contain {string}")
    public void theResponseShouldContain(String expectedText) {
        assertThat(response.asString()).contains(expectedText);
    }
}
