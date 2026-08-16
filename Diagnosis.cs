using HarmonyLib;
using UnityEngine;
using System;
using System.Reflection;

namespace Amogus
{
    public static class Diagnosis
    {
        public static void DumpTaskState(PlayerTask task)
        {
            Plugin.Instance.Log.LogInfo($"Investigating {task.TaskType}");
            Type type = task.GetType();

            Plugin.Instance.Log.LogInfo("Fields:");
            foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                try
                {
                    var val = field.GetValue(task);
                    Plugin.Instance.Log.LogInfo($"  {field.Name} = {val}");
                }
                catch {}
            }

            Plugin.Instance.Log.LogInfo("Properties:");
            foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                try
                {
                    if (prop.CanRead)
                    {
                        var val = prop.GetValue(task);
                        Plugin.Instance.Log.LogInfo($"  {prop.Name} = {val}");
                    }
                }
                catch {}
            }
        }
    }
}