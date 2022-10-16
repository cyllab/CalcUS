from frontend.models import (
    Step,
    Flowchart,
    Parameters,
    FlowchartOrder,
    Calculation,
    CalculationOrder,
)

allObjects = Calculation.objects.all()
print(allObjects)
Calculation.objects.all().delete()
# Flowchart.objects.all().delete()
# Step.objects.all().delete()

# allObjects = Step.objects.all()
# allFields = Step._meta.get_fields()
# print(allObjects)
# # for i in range(Flowchart.objects.all().count()):
# #     print(Flowchart.objects.all()[i].step_set.all())
# #     allSteps = Flowchart.objects.all()[i]
# #     print(allSteps.step_set.all())
# print(allFields)
# print(allObjects.count())
# for i in range(allObjects.count()):
#     print(allObjects[i].name)
#     print(allObjects[i].id)
#     print(allObjects[i].flowchart)
#     if(allObjects[i].parentId == None):
#         print("None")
#     else:
#         print(allObjects[i].parentId.id)
#     if(allObjects[i].step == None):
#         print("No Step")
#     else:
#         print(allObjects[i].step)
#     if(allObjects[i].parameters is not None):
#         print(allObjects[i].parameters)
#     else:
#         print("No Parameters")
#     print()

# print(FlowchartOrder.objects.all())
# allObjects = FlowchartOrder.objects.all()
# print(allObjects.count())
# for i in range(allObjects.count()):
#     print(i)
#     print(allObjects[i])
#     print(allObjects[i].name)
#     print(allObjects[i].structure)
#     print(allObjects[i].author)
#     print(allObjects[i].project)
