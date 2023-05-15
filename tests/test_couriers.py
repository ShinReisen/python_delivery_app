from httpx import AsyncClient


async def test_add_couriers(async_client: AsyncClient):
    response = await async_client.post("/couriers/", json={
                  "couriers": [
                                {
                                  "courier_type": "FOOT",
                                  "regions": [
                                    1
                                  ],
                                  "working_hours": [
                                    "11:00-15:00"
                                  ]
                                },
                                {
                                  "courier_type": "BIKE",
                                  "regions": [
                                      1, 2
                                  ],
                                  "working_hours": [
                                      "11:00-15:00", "17:00-19:00"
                                  ]
                                  },
                                  {
                                      "courier_type": "AUTO",
                                      "regions": [
                                          1, 2, 3
                                      ],
                                      "working_hours": [
                                          "09:00-12:00", "13:00-21:00"
                                      ]
                                  }
                            ]
    })

    assert response.status_code == 200

async def test_get_couriers(async_client: AsyncClient):
    response = await async_client.get("/couriers/", params={"limit": 100}
    )

    assert response.status_code == 200
    print(response.json())
    assert len(response.json()) == 3