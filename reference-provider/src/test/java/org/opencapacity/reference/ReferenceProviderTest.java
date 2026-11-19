/*
 * Copyright 2026 Ian Jones. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
 * file except in compliance with the License.
 *
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS
 * OF ANY KIND, either express or implied. See the License for the specific language
 * governing permissions and limitations under the License.
 */

package org.opencapacity.reference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.junit.jupiter.api.Test;

/** Drives the provider over HTTP with the JDK client and no OpenCapacity client library. */
class ReferenceProviderTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private final HttpClient http = HttpClient.newHttpClient();

    private JsonNode send(HttpRequest request, int expectedStatus) throws Exception {
        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
        assertEquals(expectedStatus, response.statusCode(), response.body());
        return JSON.readTree(response.body());
    }

    @Test
    void answersAQueryFromTheSyntheticInventory() throws Exception {
        try (ReferenceProvider provider = ReferenceProvider.start()) {
            JsonNode capabilities = send(HttpRequest.newBuilder(URI.create(provider.endpoint() + "/capabilities")).build(), 200);
            assertEquals("1.0.0", capabilities.path("specVersion").asText());

            String basic = Base64.getEncoder().encodeToString(
                    (ReferenceProvider.CLIENT_ID + ":" + ReferenceProvider.CLIENT_SECRET).getBytes(StandardCharsets.UTF_8));
            JsonNode token = send(HttpRequest.newBuilder(URI.create(capabilities.path("authentication").path("tokenUrl").asText()))
                    .header("Authorization", "Basic " + basic)
                    .POST(HttpRequest.BodyPublishers.ofString("grant_type=client_credentials")).build(), 200);
            String bearer = "Bearer " + token.path("access_token").asText();

            String query = """
                    {"requirement": {
                      "locations": [{"level": "METRO", "code": "FR"}],
                      "demand": {"cabinets": {"count": 40}, "density": {"target": 20, "unit": "KW"}},
                      "desiredFeatures": [{"feature": "LIQUID_COOLING", "required": true}]}}
                    """;
            JsonNode answer = send(HttpRequest.newBuilder(URI.create(provider.endpoint() + "/queries"))
                    .header("Authorization", bearer).header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(query)).build(), 200);
            assertEquals("AVAILABLE", answer.path("grade").asText());
            JsonNode result = answer.path("results").get(0);
            assertEquals("AVAILABLE", result.path("supportedFeatures").get(0).path("support").asText());
            assertEquals(40, result.path("cabinets").path("min").asInt());
            assertFalse(result.path("cabinets").has("max"), "the answer does not reveal how much is left");

            JsonNode problem = send(HttpRequest.newBuilder(URI.create(provider.endpoint() + "/queries"))
                    .header("Authorization", bearer).header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString("{\"requirement\": {\"locations\": []}}")).build(), 422);
            assertEquals("INVALID_REQUEST", problem.path("code").asText());

            send(HttpRequest.newBuilder(URI.create(provider.endpoint() + "/locations")).build(), 401);
        }
    }
}
