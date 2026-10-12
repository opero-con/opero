# ToDo identifiers use a yearly series

- **Status:** Accepted

Name new ToDos `TDO-YYNNN`, for example `TDO-26001` in 2026 and `TDO-27001`
in 2027. Use Frappe's standard autoname series `TDO-.YY.###` through a Property
Setter. The year comes from the site clock when the record is created, and each
year has its own counter. Three digits is a minimum; the counter grows past 999.

The same configuration applies to manual and assignment-created ToDos. Titles
remain separate and descriptive. Do not rename existing records or reset existing
series counters during migration. Do not add a custom naming controller.
