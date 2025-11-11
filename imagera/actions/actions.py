from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from aiohttp import ClientSession
import asyncio
import json

internal_base_url = "http://django:8000/api/v1/"


class ActionProvideProductInfo(Action):

    def name(self) -> Text:
        return "action_provide_product_info"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        product_name = next(tracker.get_latest_entity_values("product"), None)
        if product_name:
            async with ClientSession() as session:
                async with session.get(
                    internal_base_url
                    + "products/search-product-view/?products="
                    + product_name
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        product_info = json.loads(data)
                    else:
                        response = "Sorry, I couldn't find that product."
        else:
            response = "Please provide a product name."
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []


class ActionProvideProductVariation(Action):

    def name(self) -> Text:
        return "action_provide_product_variation"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        product_name = next(tracker.get_latest_entity_values("product"), None)
        if product_name:
            async with ClientSession() as session:
                async with session.get(
                    internal_base_url
                    + "products/search-product-view/?products="
                    + product_name
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        product_info = json.loads(data)
                    else:
                        response = "Sorry, I couldn't find that product."
        else:
            response = "Please provide a product name."
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []


class ActionCheckStock(Action):

    def name(self) -> Text:
        return "action_check_stock"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        product_name = next(tracker.get_latest_entity_values("product"), None)
        if product_name:
            async with ClientSession() as session:
                async with session.get(
                    internal_base_url
                    + f"products/search-product-view/?products={product_name}&in_stock=true".format(
                        product_name
                    )
                ) as response:

                    if response.status == 200:
                        data = await response.text()
                        product_info =json.loads(data)
                    else:
                        response = "Sorry, I couldn't find that product."
        else:
            response = "Please provide a product name."
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []


class ActionInformSales(Action):

    def name(self) -> Text:
        return "action_inform_sales"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        async with ClientSession() as session:
            async with session.get(
                internal_base_url + "products/sale-product-view/"
            ) as response:
                if response.status == 200:
                    data = await response.text()
                    product_info = json.loads(data)
                else:
                    response = "Sorry,There is no on going sale!"
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []


class ActionInformComboDiscount(Action):

    def name(self) -> Text:
        return "action_inform_combo_discount"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        async with ClientSession() as session:
            async with session.get(
                internal_base_url + "products/view_comboproduct/"
            ) as response:
                if response.status == 200:
                    data = await response.text()
                    product_info = json.loads(data)
                else:
                    response = "Currently, there are no combo discounts."
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []


class ActionCheckDelivery(Action):

    def name(self) -> Text:
        return "action_check_delivery"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        product_name = next(tracker.get_latest_entity_values("product"), None)
        district = next(tracker.get_latest_entity_values("district"), None)
        if product_name and district:
            async with ClientSession() as session:
                async with session.get(
                    internal_base_url
                    + "products/check-forbidden-delivery/{product_name}/{district}/"
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        product_info = json.loads(data)
                    else:
                        response = "Can't find specified product"
        else:
            response = "Please specify a product name and a district."
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []


class ActionTrackOrderDetails(Action):

    def name(self) -> Text:
        return "action_track_order_details"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        order_code = next(tracker.get_latest_entity_values("ordercode"), None)
        email = next(tracker.get_latest_entity_values("email"), None)
        if order_code and email:
            async with ClientSession() as session:
                async with session.get(
                    internal_base_url + "orders/track-order/{order_code}/{email}/"
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        product_info = json.loads(data)
                    else:
                        response = "Currently, there are no combo discounts."
        else:
            response = "Please specify an order code and an email address."
        if product_info:
            dispatcher.utter_message(json_message=product_info)
        else:
            dispatcher.utter_message(text=response)
        return []
