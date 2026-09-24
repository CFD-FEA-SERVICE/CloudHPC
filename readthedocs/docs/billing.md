# Billing Information

To set your billing information, open the "_Account_" menu and go to your profile page on the [cloudHPC platform](https://cloud.cfdfeaservice.it).

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
| _Fiscal Code or NIN_     | Italian fiscal code, if available.                                          |
| _SDI or PEC_             | Italian SDI code or PEC address, if available.                               |
| _Email_                  | Email address where invoices are sent once they are generated.              |

## Payment Methods
At the bottom of the billing information, open the "Payment Methods" section to add your preferred payment methods. The system currently accepts:

- Credit/Debit cards
- SEPA Direct Debit (available for EU clients only)

!!! note
    Once your account is activated, at least one payment method must be available at all times. To change your payment method, add the new one first and then remove the old one.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/PaymentMethod.png">
</p>

## Pricing
cloudHPC pricing is designed to be as simple as possible. The basic pricing unit is the vCPU Hour: one vCPU used for one hour. The base cost of a vCPU Hour is listed on the pricing section of [our website](https://cloudhpc.cloud/#pricing). There are no other costs: if you do not run any analysis in a given month, you are not charged anything.

The service is post-paid: you run your analyses during the month and, at the end of the month, you receive an email summarising the total vCPU Hours used. The payment is then processed within 3 to 7 days using the selected [payment method](billing.md#payment_methods).

!!! note
    Each time you launch a new simulation, a notification at the bottom of the page shows its hourly cost, based on the vCPU and RAM you selected.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/HourlyCost.png">
</p>

## Monitor Monthly Usage
The DASHBOARD menu shows your monthly vCPU Hour usage. The simulation hours are grouped by RAM type and multiplied by the number of vCPU used, and the data are collected on a monthly and yearly basis. The table also reports the cloudHPC cost of each month: for past months this is the final balance, while for the current month it is an estimate. Once the invoice has been issued, you can download it with the _Download_ button.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/FIG_21_DASHBORAD.png">
</p>

Each month only includes the vCPU Hours used within that month: if a simulation runs across two months, its cost is split between them.

## Email Notification of Consumption
cloudHPC automatically sends a consumption notification every time your usage reaches a set threshold or one of its multiples. The default threshold for all accounts is €250, so notifications are sent at €250, €500, €750, and so on.

<p align="center">
   <img width="400" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/NotificationConsumption.jpg">
</p>

Keep in mind that these notifications are based on a quick calculation and may under- or overestimate the actual consumption of your account. For example, they do not include the progressive discount applied by default at the end of each month.

## Report of Performed Simulations
From the simulations page you can download a complete report of your analyses in CSV format. The report contains all the fields shown on the simulations page, such as _Folder_, _vCPU/Hrs_ and _Cost_, and can be opened in Excel for further processing.

<p align="center">
   <a href="https://www.youtube.com/watch?v=Xiapfw2D_J4&t=18s"><img width="460" height="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/YoutubeVideo.png"></a>
</p>

