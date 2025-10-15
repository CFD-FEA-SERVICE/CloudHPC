# Billing Information

To set your billing information, you can access your "_Account_" and enter your profile page on the [cloudHPC platform](https://cloud.cfdfeaservice.it).

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/Account.png">
</p>

The billing information requested is as follows:

| Field                    | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| _First Name and Last Name_ | First name and last name of the billing account owner. |
| _Company Name_           | Name of the company to display on invoices.                                  |
| _Address Line 1/2_       | Address (street/road and number).                                           |
| _Postal Code_            | Postal or ZIP code.                                                          |
| _City_                   | City.                                                                        |
| _Province or Region_     | Province, state, or region.                                                  |
| _Country_                | Country (select from available options).                                     |
| _VAT_                    | Value Added Tax or equivalent fiscal identification number.                 |
| _Fiscal Code or NIN_     | Italian fiscal code if available.                                           |
| _SDI or PEC_             | Italian SDI or PEC if available.                                             |
| _Email_                  | Email address where invoices are sent once they are generated.              |

## Payment Methods
At the bottom of the billing information, you can enter the "Payment Methods" section to add your preferred payment methods. Currently, the system accepts the following:

- Credit/Debit cards
- SEPA Direct Debit (available for EU clients only)

!!! note
    Once your account is activated, it is mandatory to have at least one payment method available at all times. If you wish to modify your payment method, add a new one first and then remove the old one.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/PaymentMethod.png">
</p>

## Pricing
The cloudHPC pricing is intended to be as simple as possible for users. The basic unit of pricing is the vCPU Hour, representing one vCPU used for one hour. The base cost of a vCPU Hour is listed on the dedicated page of [our portal](https://cloudhpc.cloud/#pricing). There are no additional costs beyond this; if you do not execute any analyses in a specific month, you will not incur any charges.

The system operates on a post-paid basis: you can run your analyses throughout the month, and at the end of the month, you will receive an email summarizing the total vCPU Hours used. The transaction is then processed within 3 to 7 days using the selected [payment method](billing.md#payment_methods).

!!! note
    Each time you execute a new simulation, the hourly cost is provided to you via a notification at the bottom of the page. This represents the hourly cost based on the settings you have selected in terms of vCPU and RAM.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/HourlyCost.png">
</p>

## Monitor Monthly Usage
The DASHBOARD menu allows you to monitor your completed monthly vCPU hour usage. The hours of simulations consumed are collected for different types of RAM used, multiplied by the number of vCPUs used. Data is collected on a monthly and yearly basis. This table also reports the cloudHPC cost for each month; for past months, this cost is the final balance, while for the current month, it is an estimation. After the invoice has been generated, you can download the invoice file using the _Download_ button.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/FIG_21_DASHBORAD.png">
</p>

Each month contains only the vCPU hours used within that specific month. Therefore, if one of your simulations runs across two different months, the total cost is split between the two months.

## Email Notification of Consumption
CloudHPC sends automatic consumption notifications whenever an assigned threshold (or its multiple) is reached. The default threshold for all accounts is €250, leading to notifications at €250, €500, €750, etc.

<p align="center">
   <img width="400" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/NotificationConsumption.jpg">
</p>

It's important to keep in mind that these notifications provide only a quick calculation and may underestimate (or overestimate) the actual consumption of your account. They do not account for, for example, the progressive discount applied by default at the end of each month.

## Report of Performed Simulations
From your simulations page, you can download a complete report of the performed analyses in CSV file format. The report contains all the fields available on the simulation page, such as _Folder_, _vCPU/Hrs_, and _Cost_. Excel can open this file extension, allowing for post-treatment of the available information.

<p align="center">
   <a href="https://www.youtube.com/watch?v=Xiapfw2D_J4&t=18s"><img width="460" height="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/YoutubeVideo.png"></a>
</p>

