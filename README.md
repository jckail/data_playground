This is a work sample of end to end knowledge of data modeling via a simple hypothetical workflow:

Objective model data in a way that is self servicable and build a dashboard to display given user events:

1. lead -- where a user signs up for the shop app
2. prospect -- where the user selects a plan avalible and creates a shop
3. customer -- where the user has paid for the given shop 
4. churn -- where the user does not pay or does not have any actions on their shop


The data should be avalible at any point in time. 
Sanky diagram would be helpful.

User Signs Up for App 
    --> Creates a shop 
        --> Pays Invoice 
            --> Repeat
        --> Deletes Shop
        --> Does Not pay Invoice 

Event Map: 

user_creation --> lead
shop_creation --> prospect
customer --> first time bill paid
churn --> deactivation, lack of payment, or shop deletion


Tables: 
----------------------------------------------------------------

global_events (hourly)

ts : timestamp as a string of the hourly partition (partition key)
pk event_id : UUID a unique id for the event 
event_time: timestamp -- actual time of the event
event_type : enum -- an enumerated value describing the event 
metadata : json 




Event Types Meta Data Structure: 
user_account_creation: 
{
    "user_id": varchar of the id of the user
    "email" :
}

user_delete_account:
{
    "user_id": varchar of the id of the user
}

user_shop_create: 
{
    "user_id"
    "shop_id"  
    "plan_id"
}

user_shop_delete:
{
    "user_id":
    "shop_id"
}





----------------------------------------------------------------
User Data (hourly)
ts timestamp as a string of the hourly partition (partition key)
pk user_id
creation_timestamp: timestamp -- actual time of the event



----------------------------------------------------------------
Shops Data (hourly)
ts timestamp as a string of the hourly partition (partition key)
pk shop_id
creation_timestamp
fk owner_user_id

----------------------------------------------------------------
Dim Plan (hourly)
ts  timestamp as a string of the hourly partition (partition key)
pk  plan_id
invoice_amount


----------------------------------------------------------------
Payments data (daily)
ds : the date stamp or date_id partion of the record
pk payment_id : UUID a unique ID of the payment 
fk invoice_id : UUID a unique id of the invoice the payment is mapped to
fk user_id : the user_id of the payment


----------------------------------------------------------------
Invoices (daily) 
ds : the date stamp or date_id partion of the record
pk invoice_id : UUID a unique id of the invoice the payment is mapped to
fk user_id : the user_id of the invoice
fk shop_id : the id of the shop the invoice is associated with
invoice_timestamp: timestamp the invoice was created on
invoice_amount : amount of the invoice






