package com.example.observability.ui;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

import static org.assertj.core.api.Assertions.assertThat;

class ShoppingHomeSeleniumIT {
    @Test
    @EnabledIfSystemProperty(named = "runSelenium", matches = "true")
    void opensShoppingFrontendHomePage() {
        String baseUrl = System.getProperty("baseUrl", "http://localhost:8080");
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless=new", "--no-sandbox", "--disable-dev-shm-usage");

        WebDriver driver = new ChromeDriver(options);
        try {
            driver.get(baseUrl + "/");
            String bodyText = driver.findElement(By.tagName("body")).getText();
            assertThat(bodyText).contains("frontend");
        } finally {
            driver.quit();
        }
    }
}
