from httpx import AsyncClient


async def test_add_orders(async_client: AsyncClient):
    response = await async_client.post("/orders/", json={
                 "orders": [
            {
              "weight": 10,
              "regions": 1,
              "delivery_hours": [
                "09:00-21:00"
              ],
              "cost": 99
            },
                     {
                         "weight": 10,
                         "regions": 2,
                         "delivery_hours": [
                             "09:00-21:00"
                         ],
                         "cost": 99
                     }
          ]
    })

    assert response.status_code == 200

async def test_get_orders(async_client: AsyncClient):
    response = await async_client.get("/orders/", params={"limit": 100}
    )

    assert response.status_code == 200
    print(response.json())
    assert len(response.json()) == 2